"""AMD and Intel data from the kernel's sysfs files and per-client DRM stats (fdinfo).

Written from the kernel documentation and tested against fixtures, not real hardware.
Any file can be missing on a given card or kernel, so every value can be None.
"""
import os
import pathlib
import re
import time

from . import procfs

DRIVERS = {"amdgpu", "i915", "xe"}
UNITS = {"KiB": 1024, "MiB": 1024 ** 2, "": 1}
LOCAL_MEMORY = re.compile(r"^(vram|local)\d*$")

# Engine names by driver: amdgpu gfx/compute/enc/dec/jpeg, i915 render/video, xe rcs/ccs/vcs.
GRAPHICS = {"gfx", "render", "rcs"}
COMPUTE = {"compute", "ccs"}
# Intel's video engines do both jobs and don't report which, so they count towards both.
DECODE = {"dec", "dec_1", "video", "vcs"}
ENCODE = {"enc", "enc_1", "video", "vcs"}
JPEG = {"jpeg"}


def _read(path):
    try:
        return pathlib.Path(path).read_text().strip()
    except (OSError, UnicodeDecodeError):
        return None


def _number(path):
    text = _read(path)
    try:
        return int(text) if text is not None else None
    except ValueError:
        return None


def parse_fdinfo(text):
    """A DRM client's stats, or None when the fd isn't a DRM client we can identify."""
    pdev, client = None, None
    engines, total, alias = {}, {}, {}
    for line in text.splitlines():
        key, _, value = line.partition(":")
        value = value.strip()
        if key == "drm-pdev":
            pdev = value
        elif key == "drm-client-id":
            client = value
        elif key.startswith("drm-"):
            _parse_stat(key[4:], value, engines, total, alias)
    if pdev is None or client is None:
        return None
    # amdgpu prints drm-memory-* as an old alias of the same number, so use it only as a fallback.
    regions = {**alias, **total}
    return {"pdev": pdev, "client": client, "engines": engines, "memory": sum(regions.values())}


def _parse_stat(key, value, engines, total, alias):
    parts = value.split()
    try:
        amount = int(parts[0])
    except (IndexError, ValueError):
        return
    for prefix, field in (("engine-capacity-", "capacity"), ("total-cycles-", "total"), ("cycles-", "cycles"), ("engine-", "ns")):
        if key.startswith(prefix):
            engines.setdefault(key[len(prefix):], {})[field] = amount
            return
    for prefix, target in (("total-", total), ("memory-", alias)):
        if key.startswith(prefix) and LOCAL_MEMORY.match(key[len(prefix):]):
            unit = parts[1] if len(parts) > 1 else ""
            target[key[len(prefix):]] = amount * UNITS.get(unit, 1)


def read_clients():
    """(pid, fdinfo text) for each open DRM file we're allowed to read, which is our own processes."""
    found = []
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            fds = os.listdir(f"/proc/{name}/fd")
        except OSError:
            continue
        for fd in fds:
            try:
                if not os.readlink(f"/proc/{name}/fd/{fd}").startswith("/dev/dri/"):
                    continue
                with open(f"/proc/{name}/fdinfo/{fd}") as handle:
                    found.append((int(name), handle.read()))
            except OSError:
                continue
    return found


def _engine_percent(now, before, elapsed):
    """How busy one engine was between two readings. A counter reset reads as zero."""
    capacity = now.get("capacity") or 1
    if "cycles" in now and "total" in now:
        spent = now["total"] - before.get("total", now["total"])
        busy = now["cycles"] - before.get("cycles", now["cycles"])
        return 100.0 * max(0, busy) / spent / capacity if spent > 0 else 0.0
    if "ns" in now and elapsed > 0:
        busy = now["ns"] - before.get("ns", now["ns"])
        return 100.0 * max(0, busy) / (elapsed * 1e9) / capacity
    return 0.0


def _sum_class(engines, names):
    return sum(percent for name, percent in engines.items() if name in names)


class Device:
    def __init__(self, path, driver, address, name):
        self.path = path
        self.driver = driver
        self.address = address
        self.name = name
        self.device = path / "device"
        hwmons = sorted((self.device / "hwmon").glob("hwmon*"))
        self.hwmon = hwmons[0] if hwmons else self.device / "hwmon" / "none"
        self.clients = {}
        self.client_time = None
        self.energy = None
        self.energy_time = None

    @property
    def is_amd(self):
        return self.driver == "amdgpu"

    @property
    def vram_total(self):
        return _number(self.device / "mem_info_vram_total") if self.is_amd else None

    @property
    def rank(self):
        """Lower sorts first, so the card people care about is the one the bar shows."""
        if self.is_amd:
            return (0, -(self.vram_total or 0))
        return (1 if self.address.startswith("0000:00:02.") else 0, 0)


class Drm:
    @classmethod
    def open(cls, root="/sys/class/drm", names=None, describe=None, clients=read_clients, clock=time.monotonic, primary=True):
        devices = []
        base = pathlib.Path(root)
        if not base.is_dir():
            return None
        for path in sorted(base.iterdir()):
            if not re.fullmatch(r"card\d+", path.name):
                continue
            try:
                driver = (path / "device" / "driver").resolve().name
                address = (path / "device").resolve().name
            except OSError:
                continue
            if driver in DRIVERS:
                name = _read(path / "device" / "product_name") or (describe(address) if describe else address)
                devices.append(Device(path, driver, address, name))
        return cls(sorted(devices, key=lambda d: d.rank), names, clients, clock, primary) if devices else None

    def __init__(self, devices, names, clients, clock, primary=True):
        self._devices = devices
        self._names = names or (lambda pid: str(pid))
        self._clients = clients
        self._clock = clock
        self._primary = primary

    def sample(self, detail):
        now = self._clock()
        # Intel has no overall busy file, so its bar number needs a process scan. The bar only shows
        # the first GPU, so skip the scan unless that's an Intel card.
        scan = detail or (self._primary and not self._devices[0].is_amd)
        clients = self._read_clients() if scan else {}
        return [self._sample_device(device, clients.get(device.address, {}), scan, now, detail) for device in self._devices]

    def _read_clients(self):
        by_card = {}
        for pid, text in sorted(self._clients()):
            parsed = parse_fdinfo(text)
            if parsed:
                by_card.setdefault(parsed["pdev"], {}).setdefault(parsed["client"], {**parsed, "pid": pid})
        return by_card

    def _client_rates(self, device, clients, now):
        """Each client's per-engine percentages. None on the first reading, which has nothing to compare."""
        if device.client_time is None:
            rates = None
        else:
            elapsed = now - device.client_time
            rates = {}
            for client, stats in clients.items():
                before = device.clients.get(client, {})
                rates[client] = {name: _engine_percent(engine, before.get(name, {}), elapsed) for name, engine in stats["engines"].items()}
        device.clients = {client: stats["engines"] for client, stats in clients.items()}
        device.client_time = now
        return rates

    def _sample_device(self, device, clients, scan, now, detail):
        rates = self._client_rates(device, clients, now) if scan else None
        engines = self._engines(rates)
        memory_used = sum(c["memory"] for c in clients.values()) if clients else None
        if _read(device.device / "power" / "runtime_status") == "suspended":
            # Reading sensors would wake the card, which on a laptop costs real battery.
            fields = dict.fromkeys(("memPct", "memUsed", "memTotal", "temp", "power", "powerLimit", "clock", "clockMax", "fan"))
            fields["usage"] = 0
        elif device.is_amd:
            fields = self._amd(device)
        else:
            fields = self._intel(device, engines, memory_used, now)
        out = {"name": device.name, "usage": fields["usage"], "memPct": fields["memPct"],
               "temp": fields["temp"], "power": fields["power"]}
        if not detail:
            return out
        out.update({
            "memUsed": fields["memUsed"],
            "memTotal": fields["memTotal"],
            "powerLimit": fields["powerLimit"],
            "clock": fields["clock"],
            "clockMax": fields["clockMax"],
            "memClock": None,
            "fan": fields["fan"],
            "pstate": None,
            "engines": {
                "graphics": fields["usage"] if device.is_amd else (engines or {}).get("graphics"),
                "encode": (engines or {}).get("encode"),
                "decode": (engines or {}).get("decode"),
                "jpeg": (engines or {}).get("jpeg"),
                "opticalFlow": None,
            },
            "processes": self._processes(clients, rates),
        })
        return out

    @staticmethod
    def _engines(rates):
        if rates is None:
            return None
        totals = {"graphics": 0.0, "encode": 0.0, "decode": 0.0, "jpeg": 0.0}
        for engines in rates.values():
            totals["graphics"] += _sum_class(engines, GRAPHICS | COMPUTE)
            totals["encode"] += _sum_class(engines, ENCODE)
            totals["decode"] += _sum_class(engines, DECODE)
            totals["jpeg"] += _sum_class(engines, JPEG)
        return {name: round(min(100.0, value), 1) for name, value in totals.items()}

    def _amd(self, device):
        used = _number(device.device / "mem_info_vram_used")
        total = device.vram_total
        power = _number(device.hwmon / "power1_average")
        if power is None:
            power = _number(device.hwmon / "power1_input")
        limit = _number(device.hwmon / "power1_cap")
        clock = _number(device.hwmon / "freq1_input")
        temp = _number(device.hwmon / "temp1_input")
        pwm = _number(device.hwmon / "pwm1")
        return {
            "usage": _number(device.device / "gpu_busy_percent"),
            "memPct": round(100.0 * used / total, 1) if used is not None and total else None,
            "memUsed": used,
            "memTotal": total,
            "temp": round(temp / 1000, 1) if temp is not None else None,
            "power": round(power / 1e6, 1) if power is not None else None,
            "powerLimit": round(limit / 1e6) if limit else None,
            "clock": round(clock / 1e6) if clock is not None else None,
            "clockMax": self._amd_max_clock(device),
            "fan": round(100 * pwm / 255) if pwm is not None else None,
        }

    @staticmethod
    def _amd_max_clock(device):
        levels = re.findall(r"(\d+)\s*Mhz", _read(device.device / "pp_dpm_sclk") or "", re.IGNORECASE)
        return max(int(level) for level in levels) if levels else None

    def _intel(self, device, engines, memory_used, now):
        temp = _number(device.hwmon / "temp2_input")
        if temp is None:
            temp = _number(device.hwmon / "temp1_input")
        limit = _number(device.hwmon / "power1_max") or _number(device.hwmon / "power2_max")
        clock, clock_max = self._intel_clocks(device)
        usage = max(engines.values()) if engines else None
        return {
            "usage": usage,
            "memPct": None,
            "memUsed": memory_used,
            "memTotal": None,
            "temp": round(temp / 1000, 1) if temp is not None else None,
            "power": self._intel_power(device, now),
            "powerLimit": round(limit / 1e6) if limit else None,
            "clock": clock,
            "clockMax": clock_max,
            "fan": None,
        }

    @staticmethod
    def _intel_clocks(device):
        if device.driver == "xe":
            freq = device.device / "tile0" / "gt0" / "freq0"
            return _number(freq / "act_freq"), _number(freq / "rp0_freq")
        return _number(device.path / "gt_act_freq_mhz"), _number(device.path / "gt_RP0_freq_mhz")

    @staticmethod
    def _intel_power(device, now):
        energy = _number(device.hwmon / "energy1_input")
        if energy is None:
            energy = _number(device.hwmon / "energy2_input")
        before, before_time = device.energy, device.energy_time
        device.energy, device.energy_time = energy, now
        if energy is None or before is None or now <= before_time:
            return None
        return round(max(0, energy - before) / (now - before_time) / 1e6, 1)

    def _processes(self, clients, rates):
        rows = []
        for client, stats in clients.items():
            engines = (rates or {}).get(client, {})
            names = set(stats["engines"])
            rows.append({
                "name": self._names(stats["pid"]),
                "memory": stats["memory"],
                "usage": min(100.0, round(_sum_class(engines, GRAPHICS | COMPUTE), 1)),
                "encode": min(100.0, round(_sum_class(engines, ENCODE), 1)),
                "decode": min(100.0, round(_sum_class(engines, DECODE), 1)),
                "compute": 1 if names & COMPUTE else 0,
                "graphics": 1 if names & GRAPHICS else 0,
            })
        grouped = procfs.group_processes(rows, "memory", 10)
        grouped.sort(key=lambda r: (r["usage"], r["memory"]), reverse=True)
        for row in grouped:
            row["type"] = "C+G" if row["compute"] and row["graphics"] else "C" if row["compute"] else "G"
            del row["compute"], row["graphics"]
        return grouped


class Combined:
    def __init__(self, sources):
        self._sources = sources

    def sample(self, detail):
        gpus = []
        for source in self._sources:
            try:
                gpus.extend(source.sample(detail))
            except Exception:  # One broken source must not hide the other GPUs.
                continue
        return gpus


def combine(*sources):
    """One source from several, in order, skipping any that aren't available."""
    available = [source for source in sources if source is not None]
    return Combined(available) if available else None
