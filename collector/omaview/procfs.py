"""Pure parsers for /proc text. They never touch the filesystem, so tests can feed them strings."""
from collections import namedtuple

CpuTimes = namedtuple("CpuTimes", "user system idle total")

VIRTUAL_FS = {
    "proc", "sysfs", "tmpfs", "devtmpfs", "devpts", "cgroup", "cgroup2", "pstore", "bpf", "tracefs",
    "debugfs", "securityfs", "configfs", "fusectl", "mqueue", "hugetlbfs", "autofs", "ramfs", "efivarfs",
    "binfmt_misc", "nsfs", "overlay", "squashfs", "rpc_pipefs", "fuse.portal", "fuse.gvfsd-fuse",
}
# Launchers whose real identity is the process name, not the executable.
WRAPPERS = {"electron", "python", "python3", "node", "bash", "sh", "java", "wine", "wine64"}


def _cpu_times(fields):
    values = [int(v) for v in fields[:8]]
    while len(values) < 8:
        values.append(0)
    user, nice, system, idle, iowait, irq, softirq, steal = values
    busy_system = system + irq + softirq + steal
    busy_user = user + nice
    return CpuTimes(busy_user, busy_system, idle + iowait, busy_user + busy_system + idle + iowait)


def parse_cpu_stat(text):
    total, cores = None, {}
    for line in text.splitlines():
        if not line.startswith("cpu"):
            break
        name, *fields = line.split()
        if name == "cpu":
            total = _cpu_times(fields)
        else:
            cores[int(name[3:])] = _cpu_times(fields)
    return {"total": total, "cores": cores}


def cpu_delta(before, after):
    elapsed = after.total - before.total
    if elapsed <= 0:
        return {"user": 0.0, "system": 0.0, "usage": 0.0}
    user = 100.0 * (after.user - before.user) / elapsed
    system = 100.0 * (after.system - before.system) / elapsed
    return {"user": round(user, 1), "system": round(system, 1), "usage": round(user + system, 1)}


def parse_meminfo(text):
    info = {}
    for line in text.splitlines():
        key, _, rest = line.partition(":")
        parts = rest.split()
        if parts:
            info[key] = int(parts[0]) * 1024
    return info


def memory_summary(info):
    total = info.get("MemTotal", 0)
    free = info.get("MemFree", 0)
    available = info.get("MemAvailable", free)
    shared = info.get("Shmem", 0)
    cache = max(0, info.get("Buffers", 0) + info.get("Cached", 0) + info.get("SReclaimable", 0) - shared)
    apps = max(0, total - free - cache - shared)
    used = total - available
    swap_total = info.get("SwapTotal", 0)
    swap_used = swap_total - info.get("SwapFree", 0)
    return {
        "total": total, "used": used, "usedPct": round(100.0 * used / total, 1) if total else 0.0,
        "apps": apps, "cache": cache, "shared": shared, "free": free,
        "swapTotal": swap_total, "swapUsed": swap_used,
    }


def parse_pressure(text):
    for line in text.splitlines():
        if line.startswith("some"):
            for token in line.split():
                if token.startswith("avg10="):
                    return float(token[6:])
    return None


def parse_net_dev(text):
    counters = {}
    for line in text.splitlines()[2:]:
        name, _, rest = line.partition(":")
        fields = rest.split()
        if len(fields) >= 9:
            counters[name.strip()] = (int(fields[0]), int(fields[8]))
    return counters


def net_totals(counters, physical):
    rx = sum(v[0] for k, v in counters.items() if k in physical)
    tx = sum(v[1] for k, v in counters.items() if k in physical)
    return rx, tx


def parse_diskstats(text, whole_disks):
    stats = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 10 and fields[2] in whole_disks:
            stats[fields[2]] = (int(fields[5]) * 512, int(fields[9]) * 512)
    return stats


def _unescape(path):
    return path.replace("\\040", " ").replace("\\011", "\t").replace("\\134", "\\")


def parse_mounts(text):
    """One volume per device. Shared btrfs subvolumes collapse onto their shortest mount point."""
    volumes = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 3 or fields[2] in VIRTUAL_FS or not fields[0].startswith("/"):
            continue
        device, mount, fs = fields[0], _unescape(fields[1]), fields[2]
        current = volumes.get(device)
        if current is None or len(mount) < len(current["mount"]):
            volumes[device] = {"device": device, "mount": mount, "fs": fs}
    return sorted(volumes.values(), key=lambda v: v["mount"])


def parse_pid_stat(line):
    open_paren, close_paren = line.index("("), line.rindex(")")
    fields = line[close_paren + 2:].split()
    return {
        "pid": int(line[:open_paren]),
        "comm": line[open_paren + 1:close_paren],
        "ticks": int(fields[11]) + int(fields[12]),
        "start": int(fields[19]),
    }


def app_name(exe, comm):
    if not exe:
        return comm
    base = exe.replace(" (deleted)", "").rsplit("/", 1)[-1]
    if not base or base in WRAPPERS or base.split(".")[0] in WRAPPERS:
        return comm
    return base


def group_processes(rows, sort_by, limit):
    groups = {}
    for row in rows:
        group = groups.setdefault(row["name"], {"name": row["name"], "count": 0})
        group["count"] += 1
        for key, value in row.items():
            if key != "name" and isinstance(value, (int, float)):
                group[key] = group.get(key, 0) + value
    ordered = sorted(groups.values(), key=lambda g: g.get(sort_by, 0), reverse=True)
    return ordered[:limit]
