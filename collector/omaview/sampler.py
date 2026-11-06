"""Turns raw readings into one JSON-ready message per tick."""
import collections

from . import procfs, sensors

HISTORY_LENGTH = 120


class History:
    def __init__(self, capacity=HISTORY_LENGTH):
        self._capacity = capacity
        self._series = {}

    def add(self, name, value):
        self._series.setdefault(name, collections.deque(maxlen=self._capacity)).append(value)

    def dump(self):
        return {name: list(values) for name, values in self._series.items()}


class Rate:
    """Bytes per second from an increasing counter. A counter reset reads as zero, not a huge negative."""

    def __init__(self):
        self._value = None
        self._time = None

    def update(self, value, now):
        previous, previous_time = self._value, self._time
        self._value, self._time = value, now
        if previous is None or now <= previous_time:
            return None
        return max(0.0, (value - previous) / (now - previous_time))


def default_read(path):
    try:
        with open(path) as handle:
            return handle.read()
    except OSError:
        return None


class Sampler:
    def __init__(self, read, clock, physical_ifaces, whole_disks, hwmon, gpu, rapl, topology,
                 passthrough, processes, volumes, disk_models, interfaces):
        self._read = read
        self._clock = clock
        self._physical_ifaces = physical_ifaces
        self._whole_disks = whole_disks
        self._hwmon = hwmon
        self._gpu = gpu
        self._rapl = rapl
        self._topology = topology()
        self._passthrough = passthrough
        self._processes = processes
        self._volumes = volumes
        self._disk_models = disk_models
        self._interfaces = interfaces
        self._history = History()
        self._cpu_before = None
        self._rates = collections.defaultdict(Rate)

    def sample(self, detail):
        now = self._clock()
        stat = self._cpu(now)
        hwmon = self._safe(self._hwmon, {"temps": [], "fans": []})
        cpu = stat["summary"]
        cpu["temp"] = sensors.cpu_temperature(hwmon["temps"])
        cpu["power"] = self._cpu_power(now)
        gpus = self._safe(lambda: self._gpu.sample(detail) if self._gpu else [], [])
        net = self._network(now)
        disk = self._disks(now)
        mem = self._memory()
        self._record(cpu, gpus, net, disk, mem)

        message = {"t": now, "detail": detail, "cpu": cpu, "gpu": gpus, "net": {"down": net[0], "up": net[1]}}
        if detail:
            cpu["freq"] = self._cpu_frequency()
            cpu["cores"] = stat["cores"]
            cpu["threads"] = self._topology
            cpu["load"] = self._load()
            cpu["uptime"] = self._uptime()
            message["gpuPassthrough"] = self._safe(self._passthrough, [])
            message["mem"] = mem
            message["disks"] = {
                "volumes": self._safe(self._volumes, []),
                "models": self._safe(self._disk_models, {}),
                "read": disk[0], "write": disk[1], "perDisk": disk[2],
            }
            message["net"]["interfaces"] = self._safe(self._interfaces, [])
            message["sensors"] = hwmon
            message["processes"] = self._safe(self._processes, {})
            message["history"] = self._history.dump()
        return message

    @staticmethod
    def _safe(function, fallback):
        try:
            return function()
        except Exception:  # A single broken source must never take the whole collector down.
            return fallback

    def _cpu(self, now):
        empty = {"user": None, "system": None, "usage": None}
        text = self._read("/proc/stat")
        if not text:
            return {"summary": dict(empty), "cores": []}
        current = procfs.parse_cpu_stat(text)
        before, self._cpu_before = self._cpu_before, current
        if before is None:
            return {"summary": dict(empty), "cores": []}
        cores = {
            cpu: procfs.cpu_delta(before["cores"][cpu], times)["usage"]
            for cpu, times in current["cores"].items() if cpu in before["cores"]
        }
        return {
            "summary": procfs.cpu_delta(before["total"], current["total"]),
            "cores": [cores.get(cpu, 0.0) for cpu in range(max(cores, default=-1) + 1)],
        }

    def _cpu_power(self, now):
        energy = self._safe(self._rapl, None)
        if energy is None:
            return None
        watts = self._rates["rapl"].update(energy, now)
        return round(watts / 1e6, 1) if watts is not None else None

    def _cpu_frequency(self):
        text = self._read("/proc/cpuinfo")
        if not text:
            return None
        speeds = [float(line.split(":")[1]) for line in text.splitlines() if line.startswith("cpu MHz")]
        return round(sum(speeds) / len(speeds)) if speeds else None

    def _network(self, now):
        text = self._read("/proc/net/dev")
        if not text:
            return (None, None)
        rx, tx = procfs.net_totals(procfs.parse_net_dev(text), self._safe(self._physical_ifaces, set()))
        return (self._rates["rx"].update(rx, now), self._rates["tx"].update(tx, now))

    def _disks(self, now):
        text = self._read("/proc/diskstats")
        if not text:
            return (None, None, {})
        stats = procfs.parse_diskstats(text, self._safe(self._whole_disks, set()))
        per_disk = {}
        read, write = None, None
        for name, (reads, writes) in stats.items():
            r = self._rates["r:" + name].update(reads, now)
            w = self._rates["w:" + name].update(writes, now)
            per_disk[name] = {"read": r, "write": w}
            if r is not None:
                read = (read or 0.0) + r
            if w is not None:
                write = (write or 0.0) + w
        return (read, write, per_disk)

    def _memory(self):
        text = self._read("/proc/meminfo")
        if not text:
            return {}
        mem = procfs.memory_summary(procfs.parse_meminfo(text))
        pressure = self._read("/proc/pressure/memory")
        mem["pressure"] = procfs.parse_pressure(pressure) if pressure else None
        return mem

    def _load(self):
        text = self._read("/proc/loadavg")
        return [float(v) for v in text.split()[:3]] if text else None

    def _uptime(self):
        text = self._read("/proc/uptime")
        return int(float(text.split()[0])) if text else None

    def _record(self, cpu, gpus, net, disk, mem):
        add = self._history.add
        if cpu["usage"] is not None:
            add("cpuUser", cpu["user"])
            add("cpuSystem", cpu["system"])
        if cpu["temp"] is not None:
            add("cpuTemp", cpu["temp"])
        if cpu["power"] is not None:
            add("cpuPower", cpu["power"])
        if gpus:
            gpu = gpus[0]
            for key, name in (("usage", "gpuUsage"), ("memPct", "gpuMemory"), ("temp", "gpuTemp"), ("power", "gpuPower")):
                if gpu.get(key) is not None:
                    add(name, gpu[key])
        if net[0] is not None:
            add("netDown", round(net[0]))
            add("netUp", round(net[1]))
        if disk[0] is not None:
            add("diskRead", round(disk[0]))
            add("diskWrite", round(disk[1]))
        if mem:
            add("memUsed", mem["usedPct"])
            if mem.get("pressure") is not None:
                add("memPressure", mem["pressure"])
            if mem["swapTotal"]:
                add("swapUsed", round(100.0 * mem["swapUsed"] / mem["swapTotal"], 1))
