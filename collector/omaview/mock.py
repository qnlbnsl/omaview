"""Deliberately awkward fake data for designing the UI: pegged values, long names, tiny numbers."""
import math
import time

GIB = 1024 ** 3


class Sampler:
    def __init__(self):
        self._n = 0

    def sample(self, detail):
        self._n += 1
        wave = (math.sin(self._n / 6) + 1) / 2
        cpu = {"user": round(40 + 30 * wave, 1), "system": 18.0, "usage": round(58 + 30 * wave, 1), "temp": 88.5, "power": 192.4}
        gpu = {"name": "NVIDIA GeForce RTX 3090", "usage": 100, "memPct": 97.5, "temp": 86, "power": 348.2}
        message = {"t": time.time(), "detail": detail, "cpu": cpu, "gpu": [gpu],
                   "net": {"down": 118_000_000 * wave, "up": 1400.0}}
        if not detail:
            return message
        cpu.update({
            "freq": 4895, "load": [31.2, 24.05, 18.9], "uptime": 32 * 86400 + 8 * 3600,
            "cores": [round(100 * ((i * 7 + self._n) % 13) / 12, 1) for i in range(32)],
            "threads": [[i, i + 16] for i in range(16)],
        })
        gpu.update({
            "memUsed": 23.4 * GIB, "memTotal": 24 * GIB, "powerLimit": 350, "clock": 1995, "clockMax": 2100, "memClock": 9751,
            "fan": 92, "pstate": 0,
            "engines": {"graphics": 100, "encode": 64, "decode": 22, "jpeg": 0, "opticalFlow": 3},
            "processes": [
                {"name": "a-really-long-process-name-that-should-truncate-cleanly", "type": "C+G", "usage": 88, "memory": 18 * GIB, "encode": 64, "decode": 0, "count": 3},
                {"name": "python3", "type": "C", "usage": 12, "memory": 3.2 * GIB, "encode": 0, "decode": 22, "count": 1},
                {"name": "Hyprland", "type": "G", "usage": 4, "memory": 512 * 1024 ** 2, "encode": 0, "decode": 0, "count": 1},
            ],
        })
        rows = [("a-really-long-process-name-that-should-truncate-cleanly", 42.5, 41 * GIB, 180e6, 90e6),
                ("chrome", 11.2, 18 * GIB, 2e6, 4e6), ("ghostty", 3.1, 900 * 1024 ** 2, 12e3, 1e3),
                ("Hyprland", 1.4, 400 * 1024 ** 2, 0.0, 0.0), ("kworker/u64:3", 0.2, 0, 0.0, 512.0)]
        table = [{"name": n, "cpu": c, "memory": m, "read": r, "write": w, "io": r + w, "count": 1} for n, c, m, r, w in rows]
        message["processes"] = {"cpu": table, "memory": table, "disk": table}
        message["gpuPassthrough"] = [{"name": "RTX A1000", "driver": "vfio-pci"}]
        message["net"]["interfaces"] = [
            {"name": "enp5s0", "kind": "ethernet", "ip": "192.0.2.18"},
            {"name": "wlp8s0", "kind": "wifi", "ip": "192.0.2.69"},
        ]
        message["mem"] = {"total": 125 * GIB, "used": 112 * GIB, "usedPct": 89.6, "apps": 88 * GIB, "cache": 14 * GIB,
                          "shared": 10 * GIB, "free": 13 * GIB, "swapTotal": 125 * GIB, "swapUsed": 96 * GIB, "pressure": 74.0}
        message["disks"] = {
            "volumes": [
                {"device": "/dev/mapper/root", "mount": "/", "fs": "btrfs", "total": 929 * GIB, "free": 12 * GIB, "usedPct": 98.7},
                {"device": "/dev/nvme1n1p1", "mount": "/boot", "fs": "vfat", "total": 2 * GIB, "free": 1.7 * GIB, "usedPct": 13.0},
            ],
            "models": {"nvme1n1": "Sabrent Rocket 4.0 1TB", "sda": "ST5000LM000-2AN170"},
            "read": 180e6 * wave, "write": 91e6, "perDisk": {"nvme1n1": {"read": 180e6, "write": 91e6}, "sda": {"read": 0.0, "write": 0.0}},
        }
        message["sensors"] = {
            "temps": [{"name": "k10temp Tctl", "value": 88.5}, {"name": "k10temp Tccd1", "value": 79.0}, {"name": "nvme Composite", "value": 61.9}],
            "fans": [{"name": "asusec CPU", "rpm": 2840}, {"name": "asusec Water Pump", "rpm": 0}],
        }
        length = 120
        def series(base, spread):
            return [round(base + spread * (math.sin((i + self._n) / 5) + 1) / 2, 1) for i in range(length)]
        message["history"] = {
            "cpuUser": series(35, 30), "cpuSystem": series(10, 12), "cpuTemp": series(70, 18), "cpuPower": series(120, 70),
            "gpuUsage": series(70, 30), "gpuMemory": series(90, 7), "gpuTemp": series(70, 16), "gpuPower": series(200, 148),
            "netDown": series(0, 118e6), "netUp": series(0, 2e6), "diskRead": series(0, 180e6), "diskWrite": series(0, 91e6),
            "memUsed": series(80, 10), "memPressure": series(50, 25), "swapUsed": series(70, 8),
        }
        return message
