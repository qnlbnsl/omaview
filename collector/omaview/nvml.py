"""NVIDIA data through the driver's own library, called directly with ctypes."""
import ctypes
import time

from . import procfs

NOT_AVAILABLE = 0xFFFFFFFFFFFFFFFF
SUCCESS = 0


class Utilization(ctypes.Structure):
    _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]


class Memory(ctypes.Structure):
    _fields_ = [("total", ctypes.c_ulonglong), ("free", ctypes.c_ulonglong), ("used", ctypes.c_ulonglong)]


class ProcessInfo(ctypes.Structure):
    _fields_ = [("pid", ctypes.c_uint), ("usedGpuMemory", ctypes.c_ulonglong),
                ("gpuInstanceId", ctypes.c_uint), ("computeInstanceId", ctypes.c_uint)]


class ProcessSample(ctypes.Structure):
    _fields_ = [("pid", ctypes.c_uint), ("timeStamp", ctypes.c_ulonglong), ("smUtil", ctypes.c_uint),
                ("memUtil", ctypes.c_uint), ("encUtil", ctypes.c_uint), ("decUtil", ctypes.c_uint)]


def memory_value(value):
    return None if value == NOT_AVAILABLE else value


class Nvml:
    @classmethod
    def open(cls, library="libnvidia-ml.so.1", names=None):
        try:
            lib = ctypes.CDLL(library)
            if lib.nvmlInit_v2() != SUCCESS:
                return None
        except (OSError, AttributeError):
            return None
        return cls(lib, names)

    def __init__(self, lib, names):
        self._lib = lib
        self._names = names or (lambda pid: str(pid))
        count = ctypes.c_uint()
        lib.nvmlDeviceGetCount_v2(ctypes.byref(count))
        self._devices = []
        for index in range(count.value):
            handle = ctypes.c_void_p()
            if lib.nvmlDeviceGetHandleByIndex_v2(index, ctypes.byref(handle)) == SUCCESS:
                self._devices.append({"handle": handle, "name": self._device_name(handle), "seen": 0})

    def _device_name(self, handle):
        buffer = ctypes.create_string_buffer(96)
        return buffer.value.decode() if self._lib.nvmlDeviceGetName(handle, buffer, 96) == SUCCESS else "GPU"

    def _uint(self, function, handle, *args):
        """Calls an NVML getter whose last argument is an unsigned int. None when unsupported."""
        fn = getattr(self._lib, function, None)
        if fn is None:
            return None
        value = ctypes.c_uint()
        return value.value if fn(handle, *args, ctypes.byref(value)) == SUCCESS else None

    def _codec(self, function, handle):
        fn = getattr(self._lib, function, None)
        if fn is None:
            return None
        value, period = ctypes.c_uint(), ctypes.c_uint()
        return value.value if fn(handle, ctypes.byref(value), ctypes.byref(period)) == SUCCESS else None

    def sample(self, detail):
        return [self._sample_device(device, detail) for device in self._devices]

    def _sample_device(self, device, detail):
        handle = device["handle"]
        util, mem = Utilization(), Memory()
        have_util = self._lib.nvmlDeviceGetUtilizationRates(handle, ctypes.byref(util)) == SUCCESS
        have_mem = self._lib.nvmlDeviceGetMemoryInfo(handle, ctypes.byref(mem)) == SUCCESS
        power = self._uint("nvmlDeviceGetPowerUsage", handle)
        out = {
            "name": device["name"],
            "usage": util.gpu if have_util else None,
            "memPct": round(100.0 * mem.used / mem.total, 1) if have_mem and mem.total else None,
            "temp": self._uint("nvmlDeviceGetTemperature", handle, 0),
            "power": round(power / 1000, 1) if power is not None else None,
        }
        if not detail:
            return out
        limit = self._uint("nvmlDeviceGetPowerManagementLimit", handle)
        out.update({
            "memUsed": mem.used if have_mem else None,
            "memTotal": mem.total if have_mem else None,
            "powerLimit": round(limit / 1000) if limit is not None else None,
            "clock": self._uint("nvmlDeviceGetClockInfo", handle, 0),
            "clockMax": self._uint("nvmlDeviceGetMaxClockInfo", handle, 0),
            "memClock": self._uint("nvmlDeviceGetClockInfo", handle, 2),
            "fan": self._uint("nvmlDeviceGetFanSpeed", handle),
            "pstate": self._uint("nvmlDeviceGetPerformanceState", handle),
            "engines": {
                "graphics": util.gpu if have_util else None,
                "encode": self._codec("nvmlDeviceGetEncoderUtilization", handle),
                "decode": self._codec("nvmlDeviceGetDecoderUtilization", handle),
                "jpeg": self._codec("nvmlDeviceGetJpgUtilization", handle),
                "opticalFlow": self._codec("nvmlDeviceGetOfaUtilization", handle),
            },
            "processes": self._processes(device),
        })
        return out

    def _running(self, handle, kind):
        for version in ("_v3", "_v2"):
            fn = getattr(self._lib, f"nvmlDeviceGet{kind}RunningProcesses{version}", None)
            if fn is None:
                continue
            count = ctypes.c_uint(128)
            infos = (ProcessInfo * 128)()
            if fn(handle, ctypes.byref(count), infos) == SUCCESS:
                return list(infos[: count.value])
        return []

    def _utilization(self, device):
        samples = (ProcessSample * 128)()
        count = ctypes.c_uint(128)
        since = ctypes.c_ulonglong(device["seen"])
        status = self._lib.nvmlDeviceGetProcessUtilization(device["handle"], samples, ctypes.byref(count), since)
        device["seen"] = int((time.time() - 1) * 1_000_000)
        if status != SUCCESS:
            return {}
        latest = {}
        for sample in samples[: count.value]:
            current = latest.get(sample.pid)
            if current is None or sample.timeStamp > current.timeStamp:
                latest[sample.pid] = sample
        return latest

    def _processes(self, device):
        rows = {}
        for kind, flag in (("Compute", "compute"), ("Graphics", "graphics")):
            for info in self._running(device["handle"], kind):
                row = rows.setdefault(info.pid, {"name": self._names(info.pid), "memory": 0, "usage": 0, "encode": 0,
                                                 "decode": 0, "compute": 0, "graphics": 0})
                row[flag] = 1
                used = memory_value(info.usedGpuMemory)
                if used:
                    row["memory"] = max(row["memory"], used)
        for pid, sample in self._utilization(device).items():
            row = rows.get(pid)
            if row:
                row["usage"] = sample.smUtil
                row["encode"] = sample.encUtil
                row["decode"] = sample.decUtil
        grouped = procfs.group_processes(rows.values(), "memory", 10)
        grouped.sort(key=lambda r: (r["usage"], r["memory"]), reverse=True)
        for row in grouped:
            row["type"] = "C+G" if row["compute"] and row["graphics"] else "C" if row["compute"] else "G"
            del row["compute"], row["graphics"]
        return grouped
