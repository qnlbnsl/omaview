import pathlib
import tempfile
import unittest
from omaview import sensors


def hwmon(root, index, name, **files):
    path = pathlib.Path(root) / f"hwmon{index}"
    path.mkdir()
    (path / "name").write_text(name + "\n")
    for key, value in files.items():
        (path / key).write_text(f"{value}\n")


class Hwmon(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_reads_labelled_temperatures_in_celsius(self):
        hwmon(self.tmp.name, 0, "k10temp", temp1_input=41625, temp1_label="Tctl")
        data = sensors.read_hwmon(self.tmp.name)
        self.assertEqual(data["temps"], [{"name": "k10temp Tctl", "value": 41.6}])

    def test_reads_fans_and_skips_unreadable_values(self):
        hwmon(self.tmp.name, 1, "asus", fan1_input=1200, fan1_label="CPU", fan2_input="bad")
        self.assertEqual(sensors.read_hwmon(self.tmp.name)["fans"], [{"name": "asus CPU", "rpm": 1200}])

    def test_cpu_temperature_prefers_tctl(self):
        temps = [{"name": "nvme Composite", "value": 30.0}, {"name": "k10temp Tctl", "value": 44.0}]
        self.assertEqual(sensors.cpu_temperature(temps), 44.0)

    def test_cpu_temperature_finds_intel_package(self):
        temps = [{"name": "coretemp Package id 0", "value": 55.0}]
        self.assertEqual(sensors.cpu_temperature(temps), 55.0)

    def test_cpu_temperature_is_none_when_unknown(self):
        self.assertIsNone(sensors.cpu_temperature([{"name": "nvme Composite", "value": 30.0}]))


class Topology(unittest.TestCase):
    def test_pairs_sibling_threads_by_physical_core(self):
        cores = {0: (0, 0), 1: (0, 1), 2: (0, 0), 3: (0, 1)}
        self.assertEqual(sensors.pair_threads(cores), [[0, 2], [1, 3]])


if __name__ == "__main__":
    unittest.main()
