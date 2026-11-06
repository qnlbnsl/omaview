import unittest
from omaview import procfs


class CpuStat(unittest.TestCase):
    TEXT = (
        "cpu  100 0 50 800 50 0 0 0 0 0\n"
        "cpu0 60 0 20 400 20 0 0 0 0 0\n"
        "cpu1 40 0 30 400 30 0 0 0 0 0\n"
        "intr 1 2 3\n"
    )

    def test_parses_total_and_each_core(self):
        stat = procfs.parse_cpu_stat(self.TEXT)
        self.assertEqual(stat["total"].total, 1000)
        self.assertEqual(sorted(stat["cores"]), [0, 1])

    def test_delta_splits_user_and_system_percent(self):
        before = procfs.parse_cpu_stat("cpu  0 0 0 0 0 0 0 0\n")["total"]
        after = procfs.parse_cpu_stat("cpu  20 0 10 70 0 0 0 0\n")["total"]
        self.assertEqual(procfs.cpu_delta(before, after), {"user": 20.0, "system": 10.0, "usage": 30.0})

    def test_delta_with_no_elapsed_ticks_is_zero(self):
        same = procfs.parse_cpu_stat("cpu  5 0 5 5 0 0 0 0\n")["total"]
        self.assertEqual(procfs.cpu_delta(same, same)["usage"], 0.0)


class Memory(unittest.TestCase):
    TEXT = (
        "MemTotal: 1000 kB\nMemFree: 100 kB\nMemAvailable: 400 kB\nBuffers: 50 kB\n"
        "Cached: 300 kB\nSReclaimable: 50 kB\nShmem: 100 kB\nSwapTotal: 200 kB\nSwapFree: 150 kB\n"
    )

    def test_summary_reports_bytes_and_used_percent(self):
        mem = procfs.memory_summary(procfs.parse_meminfo(self.TEXT))
        self.assertEqual(mem["total"], 1000 * 1024)
        self.assertEqual(mem["used"], 600 * 1024)
        self.assertEqual(mem["usedPct"], 60.0)
        self.assertEqual(mem["swapUsed"], 50 * 1024)

    def test_breakdown_parts_add_up_to_total(self):
        mem = procfs.memory_summary(procfs.parse_meminfo(self.TEXT))
        self.assertEqual(mem["apps"] + mem["cache"] + mem["shared"] + mem["free"], mem["total"])

    def test_pressure_reads_some_avg10(self):
        text = "some avg10=12.50 avg60=1.00 avg300=0.00 total=5\nfull avg10=2.00 avg60=0 avg300=0 total=1\n"
        self.assertEqual(procfs.parse_pressure(text), 12.5)


class Network(unittest.TestCase):
    TEXT = (
        "Inter-|   Receive  |  Transmit\n face |bytes packets|bytes\n"
        "    lo: 500 1 0 0 0 0 0 0 500 1 0 0 0 0 0 0\n"
        "enp5s0: 1000 1 0 0 0 0 0 0 2000 1 0 0 0 0 0 0\n"
        "virbr0: 7 1 0 0 0 0 0 0 9 1 0 0 0 0 0 0\n"
    )

    def test_parses_rx_and_tx_per_interface(self):
        self.assertEqual(procfs.parse_net_dev(self.TEXT)["enp5s0"], (1000, 2000))

    def test_totals_count_only_physical_interfaces(self):
        counters = procfs.parse_net_dev(self.TEXT)
        self.assertEqual(procfs.net_totals(counters, physical={"enp5s0"}), (1000, 2000))


class Disks(unittest.TestCase):
    def test_diskstats_converts_sectors_to_bytes_for_whole_disks_only(self):
        text = (
            " 259 0 nvme1n1 1 0 10 0 2 0 20 0 0 0 0\n"
            " 259 1 nvme1n1p1 1 0 99 0 2 0 99 0 0 0 0\n"
            " 253 0 zram0 1 0 99 0 2 0 99 0 0 0 0\n"
        )
        stats = procfs.parse_diskstats(text, whole_disks={"nvme1n1"})
        self.assertEqual(stats, {"nvme1n1": (10 * 512, 20 * 512)})

    def test_mounts_keep_one_entry_per_device_and_skip_virtual_filesystems(self):
        text = (
            "proc /proc proc rw 0 0\n"
            "/dev/mapper/root /home btrfs rw 0 0\n"
            "/dev/mapper/root / btrfs rw 0 0\n"
            "/dev/nvme1n1p1 /boot vfat rw 0 0\n"
            "tmpfs /run tmpfs rw 0 0\n"
        )
        self.assertEqual(
            procfs.parse_mounts(text),
            [{"device": "/dev/mapper/root", "mount": "/", "fs": "btrfs"},
             {"device": "/dev/nvme1n1p1", "mount": "/boot", "fs": "vfat"}],
        )

    def test_mount_points_unescape_spaces(self):
        text = "/dev/sdb1 /mnt/my\\040disk ext4 rw 0 0\n"
        self.assertEqual(procfs.parse_mounts(text)[0]["mount"], "/mnt/my disk")


class Processes(unittest.TestCase):
    def test_stat_line_handles_spaces_and_parens_in_name(self):
        line = "42 (Web (Content)) S 1 2 3 4 5 6 7 8 9 10 111 222 0 0 20 0 1 0 999 100 5"
        parsed = procfs.parse_pid_stat(line)
        self.assertEqual(parsed, {"pid": 42, "comm": "Web (Content)", "ticks": 333, "start": 999})

    def test_group_combines_children_into_one_app_sorted_by_key(self):
        rows = [
            {"name": "chrome", "cpu": 1.0, "memory": 100},
            {"name": "chrome", "cpu": 2.0, "memory": 100},
            {"name": "ghostty", "cpu": 5.0, "memory": 50},
        ]
        grouped = procfs.group_processes(rows, sort_by="memory", limit=5)
        self.assertEqual(grouped[0], {"name": "chrome", "cpu": 3.0, "memory": 200, "count": 2})
        self.assertEqual(grouped[1]["name"], "ghostty")

    def test_group_respects_limit(self):
        rows = [{"name": str(i), "cpu": float(i)} for i in range(9)]
        self.assertEqual(len(procfs.group_processes(rows, sort_by="cpu", limit=5)), 5)

    def test_app_name_prefers_executable_over_truncated_comm(self):
        self.assertEqual(procfs.app_name("/opt/google/chrome/chrome (deleted)", "ThreadPoolForeg"), "chrome")

    def test_app_name_falls_back_to_comm(self):
        self.assertEqual(procfs.app_name(None, "kworker/0:1"), "kworker/0:1")

    def test_app_name_uses_friendly_wrappers(self):
        self.assertEqual(procfs.app_name("/usr/lib/electron/electron", "1Password"), "1Password")


if __name__ == "__main__":
    unittest.main()
