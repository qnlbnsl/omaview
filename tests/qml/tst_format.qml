import QtQuick
import QtTest
import "../../lib/format.js" as F

TestCase {
  name: "Format"

  function test_percent() {
    compare(F.percent(41.3), "41%")
    compare(F.percent(0), "0%")
    compare(F.percent(null), "–")
  }
  function test_temperature_units() {
    compare(F.temp(45.2, false), "45°")
    compare(F.temp(45, true), "113°")
    compare(F.temp(null, false), "–")
  }
  function test_watts() {
    compare(F.watts(120.4), "120W")
    compare(F.watts(null), "–")
  }
  function test_bytes_use_1024() {
    compare(F.bytes(0), "0 B")
    compare(F.bytes(1536), "1.5 KB")
    compare(F.bytes(125.7 * 1024 * 1024 * 1024), "126 GB")
    compare(F.bytes(2.5 * 1024 * 1024 * 1024 * 1024), "2.5 TB")
    compare(F.bytes(null), "–")
  }
  function test_rate_uses_1000_and_stays_short() {
    compare(F.rate(0), "0 B/s")
    compare(F.rate(999), "999 B/s")
    compare(F.rate(1400), "1.4 KB/s")
    compare(F.rate(118000000), "118 MB/s")
    compare(F.rate(1250000000), "1.3 GB/s")
    compare(F.rate(null), "–")
  }
  function test_duration() {
    compare(F.duration(32 * 86400 + 8 * 3600), "32d 8h")
    compare(F.duration(3700), "1h 1m")
    compare(F.duration(59), "0m")
    compare(F.duration(null), "–")
  }
  function test_mhz() {
    compare(F.clock(4895), "4.9 GHz")
    compare(F.clock(210), "210 MHz")
    compare(F.clock(null), "–")
  }
  function test_bar_text() {
    compare(F.barSection("CPU", { usage: 41.2, temp: 45.1, power: 120.3 }, false), "CPU 41% 45° 120W")
    compare(F.barSection("GPU", null, false), "GPU – – –")
    compare(F.barNetwork({ up: 1400, down: 118000000 }), "↑ 1.4 KB/s ↓ 118 MB/s")
    compare(F.barNetwork(null), "↑ – ↓ –")
  }
  function test_quote_survives_single_quotes() {
    compare(F.shellQuote("it's"), "'it'\\''s'")
  }
}
