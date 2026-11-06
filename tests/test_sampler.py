import unittest
from omaview.sampler import History, Rate, Sampler


class Fixed:
    """Reads a scripted filesystem so samples are deterministic."""

    def __init__(self):
        self.tick = 0

    def read(self, path):
        t = self.tick
        return {
            "/proc/stat": f"cpu  {20*t} 0 {10*t} {70*t} 0 0 0 0\ncpu0 {20*t} 0 {10*t} {70*t} 0 0 0 0\n",
            "/proc/net/dev": f"h\nh\neth0: {1000*t} 0 0 0 0 0 0 0 {500*t} 0 0 0 0 0 0 0\n",
            "/proc/diskstats": f" 8 0 sda 0 0 {2*t} 0 0 0 {4*t} 0 0 0 0\n",
            "/proc/meminfo": "MemTotal: 1000 kB\nMemFree: 500 kB\nMemAvailable: 600 kB\n",
            "/proc/pressure/memory": "some avg10=1.00 avg60=0 avg300=0 total=0\n",
            "/proc/loadavg": "1.00 2.00 3.00 1/2 3\n",
            "/proc/uptime": "3600.00 0\n",
            "/proc/vmstat": "pgpgin 0\npgpgout 0\n",
            "/proc/mounts": "",
        }.get(path)


def make(env):
    return Sampler(
        read=env.read, clock=lambda: float(env.tick * 2), physical_ifaces=lambda: {"eth0"},
        whole_disks=lambda: {"sda"}, hwmon=lambda: {"temps": [], "fans": []}, gpu=None,
        rapl=lambda: None, topology=lambda: [[0]], passthrough=lambda: [], processes=lambda: [],
        volumes=lambda: [], disk_models=lambda: {}, interfaces=lambda: [],
    )


class Sampling(unittest.TestCase):
    def test_second_sample_reports_cpu_percent_and_network_rate(self):
        env = Fixed()
        sampler = make(env)
        sampler.sample(detail=False)
        env.tick = 1
        out = sampler.sample(detail=False)
        self.assertEqual(out["cpu"]["usage"], 30.0)
        self.assertEqual(out["net"], {"down": 500.0, "up": 250.0})

    def test_bar_only_sample_omits_detail_sections(self):
        env = Fixed()
        out = make(env).sample(detail=False)
        self.assertNotIn("history", out)
        self.assertNotIn("mem", out)

    def test_detail_sample_includes_history_and_sections(self):
        env = Fixed()
        sampler = make(env)
        sampler.sample(detail=False)
        env.tick = 1
        out = sampler.sample(detail=True)
        self.assertEqual(out["history"]["cpuUser"], [20.0])
        self.assertEqual(out["mem"]["usedPct"], 40.0)
        self.assertEqual(out["cpu"]["load"], [1.0, 2.0, 3.0])
        self.assertEqual(out["cpu"]["uptime"], 3600)

    def test_history_keeps_recording_while_nothing_is_open(self):
        env = Fixed()
        sampler = make(env)
        for env.tick in range(1, 4):
            sampler.sample(detail=False)
        self.assertEqual(len(sampler.sample(detail=True)["history"]["cpuUser"]), 3)

    def test_failing_source_leaves_null_instead_of_crashing(self):
        env = Fixed()
        sampler = make(env)
        sampler._read = lambda path: None
        out = sampler.sample(detail=True)
        self.assertIsNone(out["cpu"]["usage"])
        self.assertIsNone(out["net"]["down"])
        self.assertIsNone(out["net"]["up"])


class Helpers(unittest.TestCase):
    def test_history_drops_oldest_past_capacity(self):
        history = History(2)
        for value in (1, 2, 3):
            history.add("x", value)
        self.assertEqual(history.dump()["x"], [2, 3])

    def test_rate_ignores_counter_reset(self):
        rate = Rate()
        self.assertIsNone(rate.update(100, 0.0))
        self.assertEqual(rate.update(200, 2.0), 50.0)
        self.assertEqual(rate.update(50, 4.0), 0.0)


if __name__ == "__main__":
    unittest.main()
