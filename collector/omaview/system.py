"""Live readers for things that need more than a single /proc file."""
import array
import fcntl
import functools
import os
import pathlib
import re
import socket
import struct
import subprocess
import time

from . import procfs

SIOCGIFADDR = 0x8915


def read_text(path):
    try:
        with open(path) as handle:
            return handle.read()
    except OSError:
        return None


def physical_interfaces(root="/sys/class/net"):
    base = pathlib.Path(root)
    return {path.name for path in base.iterdir() if (path / "device").exists()} if base.is_dir() else set()


def _ipv4(name):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            packed = fcntl.ioctl(sock.fileno(), SIOCGIFADDR, struct.pack("256s", name[:15].encode()))
        except OSError:
            return None
    return socket.inet_ntoa(packed[20:24])


def interfaces(root="/sys/class/net"):
    result = []
    for name in sorted(physical_interfaces(root)):
        path = pathlib.Path(root) / name
        if (read_text(path / "operstate") or "").strip() != "up":
            continue
        result.append({"name": name, "kind": "wifi" if (path / "wireless").exists() else "ethernet", "ip": _ipv4(name)})
    return result


def whole_disks(root="/sys/block"):
    base = pathlib.Path(root)
    return {path.name for path in base.iterdir() if (path / "device").exists()} if base.is_dir() else set()


def disk_models(root="/sys/block"):
    models = {}
    for name in whole_disks(root):
        model = read_text(pathlib.Path(root) / name / "device/model")
        models[name] = model.strip() if model else name
    return models


def volumes(read=read_text):
    result = []
    for volume in procfs.parse_mounts(read("/proc/mounts") or ""):
        try:
            stat = os.statvfs(volume["mount"])
        except OSError:
            continue
        total = stat.f_blocks * stat.f_frsize
        if total == 0:
            continue
        free = stat.f_bavail * stat.f_frsize
        used = total - stat.f_bfree * stat.f_frsize
        result.append({**volume, "total": total, "free": free, "usedPct": round(100.0 * used / total, 1)})
    return result


def rapl_energy(path="/sys/class/powercap/intel-rapl:0/energy_uj"):
    text = read_text(path)
    return int(text) if text else None


@functools.lru_cache(maxsize=16)
def describe_pci(address):
    try:
        out = subprocess.run(["lspci", "-s", address], capture_output=True, text=True, timeout=2).stdout
    except (OSError, subprocess.SubprocessError):
        return address
    match = re.search(r"\[([^\]]+)\]\s*(\(rev [^)]*\))?\s*$", out.strip())
    return match.group(1) if match else (out.split(": ", 1)[-1].strip() or address)


def passthrough_gpus(root="/sys/bus/pci/devices", describe=describe_pci):
    found = []
    base = pathlib.Path(root)
    if not base.is_dir():
        return found
    for device in sorted(base.iterdir()):
        cls = read_text(device / "class")
        if not cls or not cls.startswith("0x03"):
            continue
        driver = device / "driver"
        if driver.exists() and driver.resolve().name == "vfio-pci":
            found.append({"name": describe(device.name), "driver": "vfio-pci"})
    return found


def _exe(pid):
    try:
        return os.readlink(f"/proc/{pid}/exe")
    except OSError:
        return None


def _list_pids():
    return [int(name) for name in os.listdir("/proc") if name.isdigit()]


class ProcessTable:
    """Per-process CPU, private memory and disk rates. Only runs while a report is open."""

    LIMIT = 10

    def __init__(self, list_pids=_list_pids, read=read_text, exe=_exe, clk_tck=None, page_size=None, cpu_count=None):
        self._list_pids = list_pids
        self._read = read
        self._exe = exe
        self._clk_tck = clk_tck or os.sysconf("SC_CLK_TCK")
        self._page_size = page_size or os.sysconf("SC_PAGE_SIZE")
        self._cpu_count = cpu_count or os.cpu_count() or 1
        self._before = {}
        self._time = None
        self._names = {}

    def _name(self, pid, start, comm):
        key = (pid, start)
        if key not in self._names:
            self._names[key] = procfs.app_name(self._exe(pid), comm)
        return self._names[key]

    def _io(self, pid):
        text = self._read(f"/proc/{pid}/io")
        if not text:
            return None
        values = dict(line.split(": ") for line in text.splitlines() if ": " in line)
        return int(values.get("read_bytes", 0)), int(values.get("write_bytes", 0))

    def sample(self, now):
        elapsed = now - self._time if self._time is not None else 0
        current, rows = {}, []
        for pid in self._list_pids():
            stat_text = self._read(f"/proc/{pid}/stat")
            statm_text = self._read(f"/proc/{pid}/statm")
            if not stat_text or not statm_text:
                continue
            try:
                stat = procfs.parse_pid_stat(stat_text)
                resident, shared = [int(v) for v in statm_text.split()[1:3]]
            except (ValueError, IndexError):
                continue
            io = self._io(pid)
            current[pid] = (stat["start"], stat["ticks"], io)
            row = {"name": self._name(pid, stat["start"], stat["comm"]), "cpu": 0.0,
                   "memory": max(0, resident - shared) * self._page_size, "read": 0.0, "write": 0.0}
            before = self._before.get(pid)
            if before and before[0] == stat["start"] and elapsed > 0:
                seconds = (stat["ticks"] - before[1]) / self._clk_tck
                row["cpu"] = round(100.0 * seconds / elapsed / self._cpu_count, 2)
                if io and before[2]:
                    row["read"] = max(0.0, (io[0] - before[2][0]) / elapsed)
                    row["write"] = max(0.0, (io[1] - before[2][1]) / elapsed)
            row["io"] = row["read"] + row["write"]
            rows.append(row)
        self._before, self._time = current, now
        live = {(pid, value[0]) for pid, value in current.items()}
        self._names = {key: name for key, name in self._names.items() if key in live}
        return {
            "cpu": procfs.group_processes(rows, "cpu", self.LIMIT),
            "memory": procfs.group_processes(rows, "memory", self.LIMIT),
            "disk": procfs.group_processes(rows, "io", self.LIMIT),
        }


def process_name(pid):
    comm = (read_text(f"/proc/{pid}/comm") or str(pid)).strip()
    return procfs.app_name(_exe(pid), comm)


class FreshProcesses:
    """A cold table has no deltas, so take a short baseline instead of showing a report of zeros."""

    BASELINE = 0.25
    STALE_AFTER = 10.0

    def __init__(self, table, clock=time.monotonic, sleep=time.sleep):
        self._table = table
        self._clock = clock
        self._sleep = sleep
        self._last = None

    def __call__(self):
        now = self._clock()
        if self._last is None or now - self._last > self.STALE_AFTER:
            self._table.sample(now)
            self._sleep(self.BASELINE)
            now = self._clock()
        self._last = now
        return self._table.sample(now)
