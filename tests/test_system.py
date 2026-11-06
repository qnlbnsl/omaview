import pathlib
import tempfile
import unittest
from omaview import mock, nvml, system


def fake_pci(root, address, vendor, cls, driver=None):
    device = pathlib.Path(root) / address
    device.mkdir(parents=True)
    (device / "vendor").write_text(vendor + "\n")
    (device / "class").write_text(cls + "\n")
    if driver:
        target = pathlib.Path(root) / "drivers" / driver
        target.mkdir(parents=True, exist_ok=True)
        (device / "driver").symlink_to(target)


class Passthrough(unittest.TestCase):
    def test_lists_only_display_devices_bound_to_vfio(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_pci(tmp, "0000:0d:00.0", "0x10de", "0x030000", "vfio-pci")
            fake_pci(tmp, "0000:0c:00.0", "0x10de", "0x030000", "nvidia")
            fake_pci(tmp, "0000:05:00.0", "0x10ec", "0x020000", "vfio-pci")
            found = system.passthrough_gpus(tmp, describe=lambda address: f"gpu at {address}")
        self.assertEqual(found, [{"name": "gpu at 0000:0d:00.0", "driver": "vfio-pci"}])


class ProcessTable(unittest.TestCase):
    def setUp(self):
        self.ticks = {100: 0}
        self.table = system.ProcessTable(
            list_pids=lambda: list(self.ticks),
            read=self.read,
            exe=lambda pid: "/usr/bin/ghostty",
            clk_tck=100, page_size=4096, cpu_count=2,
        )

    def read(self, path):
        pid = int(path.split("/")[2])
        if pid not in self.ticks:
            return None
        if path.endswith("/stat"):
            return f"{pid} (ghostty) S 1 2 3 4 5 6 7 8 9 10 {self.ticks[pid]} 0 0 0 20 0 1 0 500 100 5"
        if path.endswith("/statm"):
            return "1000 400 100 0 0 0 0"
        if path.endswith("/io"):
            return "read_bytes: 1000\nwrite_bytes: 4000\n"
        return None

    def test_cpu_percent_is_share_of_whole_machine(self):
        self.table.sample(now=0.0)
        self.ticks[100] = 100
        rows = self.table.sample(now=1.0)
        self.assertEqual(rows["cpu"][0]["cpu"], 50.0)

    def test_memory_counts_private_pages_only(self):
        rows = self.table.sample(now=0.0)
        self.assertEqual(rows["memory"][0]["memory"], 300 * 4096)

    def test_disk_rates_come_from_io_counters(self):
        self.table.sample(now=0.0)
        self.read_original = self.read
        self.table._read = lambda path: "read_bytes: 3000\nwrite_bytes: 4000\n" if path.endswith("/io") else self.read(path)
        rows = self.table.sample(now=2.0)
        self.assertEqual(rows["disk"][0]["read"], 1000.0)
        self.assertEqual(rows["disk"][0]["write"], 0.0)

    def test_process_that_exits_mid_scan_is_skipped(self):
        self.ticks[200] = 0
        reads = self.read
        self.table._read = lambda path: None if "/200/" in path else reads(path)
        self.assertEqual(self.table.sample(now=0.0)["cpu"][0]["count"], 1)

    def test_a_reused_pid_does_not_produce_a_cpu_spike(self):
        self.table.sample(now=0.0)
        self.ticks[100] = 5000
        original = self.read
        self.table._read = lambda path: original(path).replace(" 500 100 5", " 900 100 5") if path.endswith("/stat") else original(path)
        self.assertEqual(self.table.sample(now=1.0)["cpu"][0]["cpu"], 0.0)


class NvmlStructs(unittest.TestCase):
    def test_process_info_matches_driver_layout(self):
        self.assertEqual(nvml.ctypes.sizeof(nvml.ProcessInfo), 24)

    def test_process_utilization_sample_matches_driver_layout(self):
        self.assertEqual(nvml.ctypes.sizeof(nvml.ProcessSample), 32)

    def test_missing_library_means_no_gpu_instead_of_a_crash(self):
        self.assertIsNone(nvml.Nvml.open("libdoes-not-exist.so"))

    def test_not_available_memory_value_reads_as_none(self):
        self.assertIsNone(nvml.memory_value(0xFFFFFFFFFFFFFFFF))
        self.assertEqual(nvml.memory_value(1024), 1024)


class MockData(unittest.TestCase):
    def test_mock_detail_has_every_section_cards_read(self):
        out = mock.Sampler().sample(True)
        for key in ("cpu", "gpu", "gpuPassthrough", "net", "mem", "disks", "sensors", "processes", "history"):
            self.assertIn(key, out)
        self.assertEqual(len(out["cpu"]["threads"]), 16)

    def test_mock_bar_sample_stays_small(self):
        self.assertNotIn("history", mock.Sampler().sample(False))



class FreshProcessesTests(unittest.TestCase):
    class Table:
        def __init__(self):
            self.calls = []

        def sample(self, now):
            self.calls.append(now)
            return {"at": now}

    def test_cold_table_takes_a_short_baseline_so_first_report_is_meaningful(self):
        table = self.Table()
        times = iter([100.0, 100.25])
        slept = []
        fresh = system.FreshProcesses(table, clock=lambda: next(times), sleep=slept.append)
        self.assertEqual(fresh(), {"at": 100.25})
        self.assertEqual(table.calls, [100.0, 100.25])
        self.assertEqual(slept, [0.25])

    def test_while_reports_stay_open_it_samples_once(self):
        table = self.Table()
        times = iter([100.0, 100.25, 102.25])
        fresh = system.FreshProcesses(table, clock=lambda: next(times), sleep=lambda s: None)
        fresh()
        self.assertEqual(fresh(), {"at": 102.25})
        self.assertEqual(len(table.calls), 3)

    def test_baseline_is_retaken_after_a_long_gap(self):
        table = self.Table()
        times = iter([100.0, 100.25, 500.0, 500.25])
        fresh = system.FreshProcesses(table, clock=lambda: next(times), sleep=lambda s: None)
        fresh()
        self.assertEqual(fresh(), {"at": 500.25})
        self.assertEqual(len(table.calls), 4)


if __name__ == "__main__":
    unittest.main()
