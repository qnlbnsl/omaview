"""Reads hwmon sensors and CPU topology from sysfs."""
import pathlib


def _read(path):
    try:
        return path.read_text().strip()
    except OSError:
        return None


def _number(text):
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def read_hwmon(root="/sys/class/hwmon"):
    temps, fans = [], []
    base = pathlib.Path(root)
    if not base.is_dir():
        return {"temps": temps, "fans": fans}
    for hwmon in sorted(base.iterdir()):
        chip = _read(hwmon / "name") or hwmon.name
        for entry in sorted(hwmon.glob("temp*_input")):
            value = _number(_read(entry))
            if value is not None:
                label = _read(entry.with_name(entry.name.replace("_input", "_label")))
                temps.append({"name": f"{chip} {label}" if label else chip, "value": round(value / 1000, 1)})
        for entry in sorted(hwmon.glob("fan*_input")):
            value = _number(_read(entry))
            if value is not None:
                label = _read(entry.with_name(entry.name.replace("_input", "_label")))
                fans.append({"name": f"{chip} {label}" if label else chip, "rpm": value})
    return {"temps": temps, "fans": fans}


def cpu_temperature(temps):
    for wanted in ("k10temp Tctl", "zenpower Tdie", "zenpower Tctl", "coretemp Package"):
        for temp in temps:
            if temp["name"].startswith(wanted):
                return temp["value"]
    return None


def pair_threads(cores):
    """cores maps cpu index to (package, core). Returns one list of sibling threads per physical core."""
    physical = {}
    for cpu in sorted(cores):
        physical.setdefault(cores[cpu], []).append(cpu)
    return [physical[key] for key in sorted(physical)]


def read_topology(root="/sys/devices/system/cpu"):
    cores = {}
    for path in pathlib.Path(root).glob("cpu[0-9]*"):
        package = _number(_read(path / "topology/physical_package_id"))
        core = _number(_read(path / "topology/core_id"))
        if package is not None and core is not None:
            cores[int(path.name[3:])] = (package, core)
    return pair_threads(cores)
