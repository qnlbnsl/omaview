import pathlib
import tempfile
import unittest

from omaview import drm

ADDRESS = "0000:03:00.0"
GIB = 1024 ** 3


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def write(base, **files):
    base.mkdir(parents=True, exist_ok=True)
    for name, value in files.items():
        (base / name).write_text(f"{value}\n")


def card(root, index, driver, vendor, address=ADDRESS):
    """Builds cardN with the device symlink layout the kernel uses."""
    root = pathlib.Path(root)
    device = root / "pci" / address
    driver_dir = root / "drivers" / driver
    device.mkdir(parents=True)
    driver_dir.mkdir(parents=True, exist_ok=True)
    (device / "driver").symlink_to(driver_dir)
    (device / "vendor").write_text(vendor + "\n")
    path = root / "class" / f"card{index}"
    path.mkdir(parents=True)
    (path / "device").symlink_to(device)
    return path


def hwmon(path, **files):
    write(path / "device" / "hwmon" / "hwmon3", **files)


def amd_card(root, index=0, address=ADDRESS, vram=16 * GIB):
    path = card(root, index, "amdgpu", "0x1002", address)
    write(path / "device", gpu_busy_percent=42, mem_info_vram_used=4 * GIB, mem_info_vram_total=vram,
          pp_dpm_sclk="0: 500Mhz\n1: 2100Mhz *\n2: 2500Mhz", product_name="Radeon RX 7900 XT")
    hwmon(path, temp1_input=61000, power1_average=150_000_000, power1_cap=300_000_000,
          freq1_input=2_100_000_000, pwm1=128)
    return path


def open_drm(root, clients=lambda: [], clock=None, describe=lambda address: "described " + address, primary=True):
    return drm.Drm.open(root=pathlib.Path(root) / "class", names=lambda pid: f"app{pid}",
                        describe=describe, clients=clients, clock=clock or Clock(), primary=primary)


class ParseFdinfo(unittest.TestCase):
    def test_reads_time_and_memory_in_bytes(self):
        parsed = drm.parse_fdinfo(
            f"pos:\t0\ndrm-driver:\tamdgpu\ndrm-pdev:\t{ADDRESS}\ndrm-client-id:\t7\n"
            "drm-engine-gfx:\t5000 ns\ndrm-engine-enc:\t100 ns\ndrm-total-vram:\t2048 KiB\ndrm-total-gtt:\t999 KiB\n")
        self.assertEqual(parsed["pdev"], ADDRESS)
        self.assertEqual(parsed["client"], "7")
        self.assertEqual(parsed["engines"]["gfx"]["ns"], 5000)
        self.assertEqual(parsed["memory"], 2048 * 1024)

    def test_reads_xe_cycles(self):
        parsed = drm.parse_fdinfo(
            f"drm-pdev:\t{ADDRESS}\ndrm-client-id:\t1\ndrm-cycles-rcs:\t30\ndrm-total-cycles-rcs:\t100\n"
            "drm-engine-capacity-rcs:\t2\ndrm-total-vram0:\t1 MiB\n")
        self.assertEqual(parsed["engines"]["rcs"], {"cycles": 30, "total": 100, "capacity": 2})
        self.assertEqual(parsed["memory"], 1024 ** 2)

    def test_amdgpu_memory_alias_counts_once(self):
        parsed = drm.parse_fdinfo(f"drm-pdev:\t{ADDRESS}\ndrm-client-id:\t1\ndrm-memory-vram:\t4 KiB\n")
        self.assertEqual(parsed["memory"], 4096)
        parsed = drm.parse_fdinfo(f"drm-pdev:\t{ADDRESS}\ndrm-client-id:\t1\ndrm-memory-vram:\t4 KiB\ndrm-total-vram:\t4 KiB\n")
        self.assertEqual(parsed["memory"], 4096)

    def test_other_files_are_not_clients(self):
        self.assertIsNone(drm.parse_fdinfo("pos:\t0\nflags:\t02\n"))


class Discovery(unittest.TestCase):
    def test_no_supported_card_means_no_source(self):
        with tempfile.TemporaryDirectory() as root:
            card(root, 0, "nvidia", "0x10de")
            self.assertIsNone(open_drm(root))

    def test_discrete_cards_come_before_integrated_ones(self):
        with tempfile.TemporaryDirectory() as root:
            card(root, 0, "i915", "0x8086", "0000:00:02.0")
            amd_card(root, 1)
            gpus = open_drm(root).sample(False)
            self.assertEqual(gpus[0]["name"], "Radeon RX 7900 XT")
            self.assertEqual(gpus[1]["name"], "described 0000:00:02.0")

    def test_amd_with_more_vram_comes_first(self):
        with tempfile.TemporaryDirectory() as root:
            amd_card(root, 0, "0000:04:00.0", vram=GIB // 2)
            write(amd_card(root, 1, "0000:03:00.0") / "device", product_name="Big")
            self.assertEqual(open_drm(root).sample(False)[0]["name"], "Big")


class Amd(unittest.TestCase):
    def test_bar_numbers(self):
        with tempfile.TemporaryDirectory() as root:
            amd_card(root)
            gpu = open_drm(root).sample(False)[0]
            self.assertEqual(gpu, {"name": "Radeon RX 7900 XT", "usage": 42, "memPct": 25.0, "temp": 61.0, "power": 150.0})

    def test_details(self):
        with tempfile.TemporaryDirectory() as root:
            amd_card(root)
            gpu = open_drm(root).sample(True)[0]
            self.assertEqual(gpu["clock"], 2100)
            self.assertEqual(gpu["clockMax"], 2500)
            self.assertEqual(gpu["powerLimit"], 300)
            self.assertEqual(gpu["memUsed"], 4 * GIB)
            self.assertEqual(gpu["memTotal"], 16 * GIB)
            self.assertEqual(gpu["fan"], 50)
            self.assertIsNone(gpu["pstate"])
            self.assertEqual(gpu["engines"]["graphics"], 42)

    def test_missing_files_read_as_none(self):
        with tempfile.TemporaryDirectory() as root:
            card(root, 0, "amdgpu", "0x1002")
            gpu = open_drm(root).sample(True)[0]
            for key in ("usage", "memPct", "temp", "power", "clock", "clockMax", "fan", "powerLimit"):
                self.assertIsNone(gpu[key], key)

    def test_idle_bar_doesnt_scan_processes(self):
        def fail():
            raise AssertionError("scanned processes")
        with tempfile.TemporaryDirectory() as root:
            amd_card(root)
            open_drm(root, clients=fail).sample(False)

    def test_a_sleeping_card_isnt_woken(self):
        with tempfile.TemporaryDirectory() as root:
            path = amd_card(root)
            write(path / "device" / "power", runtime_status="suspended")
            gpu = open_drm(root).sample(True)[0]
            self.assertEqual(gpu["usage"], 0)
            self.assertIsNone(gpu["temp"])
            self.assertIsNone(gpu["memUsed"])

    def test_power_falls_back_to_instantaneous(self):
        with tempfile.TemporaryDirectory() as root:
            path = card(root, 0, "amdgpu", "0x1002")
            hwmon(path, power1_input=80_000_000)
            self.assertEqual(open_drm(root).sample(False)[0]["power"], 80.0)

    def test_processes_and_engines_from_fdinfo(self):
        def text(gfx, enc):
            return (f"drm-pdev:\t{ADDRESS}\ndrm-client-id:\t5\ndrm-engine-gfx:\t{gfx} ns\n"
                    f"drm-engine-enc:\t{enc} ns\ndrm-total-vram:\t1024 KiB\n")
        with tempfile.TemporaryDirectory() as root:
            amd_card(root)
            clock = Clock()
            state = [(11, text(0, 0))]
            source = open_drm(root, clients=lambda: state, clock=clock)
            source.sample(True)
            clock.now += 2
            state[:] = [(11, text(500_000_000, 1_000_000_000))]
            gpu = source.sample(True)[0]
            self.assertEqual(gpu["engines"]["encode"], 50.0)
            row = gpu["processes"][0]
            self.assertEqual((row["name"], row["memory"], row["usage"], row["encode"], row["type"]),
                             ("app11", 1024 ** 2, 25.0, 50.0, "G"))

    def test_shared_clients_count_once_and_other_cards_are_ignored(self):
        def text(ns, address=ADDRESS):
            return f"drm-pdev:\t{address}\ndrm-client-id:\t5\ndrm-engine-gfx:\t{ns} ns\n"
        with tempfile.TemporaryDirectory() as root:
            amd_card(root)
            clock = Clock()
            state = [(11, text(0)), (12, text(0))]
            source = open_drm(root, clients=lambda: state, clock=clock)
            source.sample(True)
            clock.now += 1
            state[:] = [(11, text(100_000_000)), (12, text(100_000_000)), (13, text(900_000_000, "0000:09:00.0"))]
            rows = source.sample(True)[0]["processes"]
            self.assertEqual([(r["name"], r["usage"]) for r in rows], [("app11", 10.0)])


class Intel(unittest.TestCase):
    def xe_card(self, root):
        path = card(root, 0, "xe", "0x8086")
        write(path / "device" / "tile0" / "gt0" / "freq0", act_freq=1500, rp0_freq=2400)
        hwmon(path, energy2_input=0, temp2_input=55000, power2_max=190_000_000)
        return path

    def test_xe_usage_comes_from_cycles_and_power_from_energy(self):
        def text(busy, total):
            return (f"drm-pdev:\t{ADDRESS}\ndrm-client-id:\t3\ndrm-cycles-rcs:\t{busy}\n"
                    f"drm-total-cycles-rcs:\t{total}\ndrm-total-vram0:\t2048 KiB\n")
        with tempfile.TemporaryDirectory() as root:
            path = self.xe_card(root)
            clock = Clock()
            state = [(9, text(0, 0))]
            source = open_drm(root, clients=lambda: state, clock=clock)
            first = source.sample(False)[0]
            self.assertIsNone(first["usage"])
            self.assertIsNone(first["power"])
            clock.now += 2
            state[:] = [(9, text(30, 100))]
            write(path / "device" / "hwmon" / "hwmon3", energy2_input=100_000_000)
            gpu = source.sample(True)[0]
            self.assertEqual(gpu["usage"], 30.0)
            self.assertEqual(gpu["power"], 50.0)
            self.assertEqual(gpu["temp"], 55.0)
            self.assertEqual(gpu["clock"], 1500)
            self.assertEqual(gpu["clockMax"], 2400)
            self.assertEqual(gpu["powerLimit"], 190)
            self.assertEqual(gpu["memUsed"], 2048 * 1024)
            self.assertIsNone(gpu["memTotal"])
            self.assertIsNone(gpu["memPct"])

    def test_i915_time_engines_use_capacity_and_video_counts_as_both_codecs(self):
        def text(render, video):
            return (f"drm-pdev:\t{ADDRESS}\ndrm-client-id:\t3\ndrm-engine-render:\t{render} ns\n"
                    f"drm-engine-video:\t{video} ns\ndrm-engine-capacity-video:\t2\n")
        with tempfile.TemporaryDirectory() as root:
            path = card(root, 0, "i915", "0x8086")
            write(path, gt_act_freq_mhz=1200, gt_RP0_freq_mhz=2100)
            hwmon(path, temp1_input=48000, power1_max=225_000_000, energy1_input=0)
            clock = Clock()
            state = [(9, text(0, 0))]
            source = open_drm(root, clients=lambda: state, clock=clock)
            source.sample(True)
            clock.now += 1
            state[:] = [(9, text(200_000_000, 1_000_000_000))]
            gpu = source.sample(True)[0]
            self.assertEqual(gpu["engines"]["graphics"], 20.0)
            self.assertEqual(gpu["engines"]["decode"], 50.0)
            self.assertEqual(gpu["engines"]["encode"], 50.0)
            self.assertEqual(gpu["usage"], 50.0)
            self.assertEqual(gpu["clock"], 1200)
            self.assertEqual(gpu["clockMax"], 2100)
            self.assertEqual(gpu["temp"], 48.0)

    def test_idle_gpu_with_no_clients_reads_zero_after_the_first_sample(self):
        with tempfile.TemporaryDirectory() as root:
            self.xe_card(root)
            source = open_drm(root)
            source.sample(False)
            self.assertEqual(source.sample(False)[0]["usage"], 0.0)

    def test_intel_behind_another_gpu_doesnt_scan_while_idle(self):
        def fail():
            raise AssertionError("scanned processes")
        with tempfile.TemporaryDirectory() as root:
            self.xe_card(root)
            open_drm(root, clients=fail, primary=False).sample(False)

    def test_counter_reset_reads_as_zero(self):
        def text(ns):
            return f"drm-pdev:\t{ADDRESS}\ndrm-client-id:\t3\ndrm-engine-render:\t{ns} ns\n"
        with tempfile.TemporaryDirectory() as root:
            card(root, 0, "i915", "0x8086")
            clock = Clock()
            state = [(9, text(500))]
            source = open_drm(root, clients=lambda: state, clock=clock)
            source.sample(False)
            clock.now += 1
            state[:] = [(9, text(100))]
            self.assertEqual(source.sample(False)[0]["usage"], 0.0)


class Combine(unittest.TestCase):
    class Source:
        def __init__(self, gpus):
            self.gpus = gpus

        def sample(self, detail):
            if isinstance(self.gpus, Exception):
                raise self.gpus
            return self.gpus

    def test_no_sources_is_none(self):
        self.assertIsNone(drm.combine(None, None))

    def test_earlier_sources_come_first(self):
        source = drm.combine(self.Source([{"name": "a"}]), None, self.Source([{"name": "b"}]))
        self.assertEqual([g["name"] for g in source.sample(False)], ["a", "b"])

    def test_a_broken_source_doesnt_hide_the_others(self):
        source = drm.combine(self.Source(RuntimeError("boom")), self.Source([{"name": "b"}]))
        self.assertEqual([g["name"] for g in source.sample(False)], ["b"])


if __name__ == "__main__":
    unittest.main()
