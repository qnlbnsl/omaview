import QtQuick
import QtTest
import "../../lib/metrics.js" as M
import "../../lib/layout.js" as L

TestCase {
  name: "Metrics"

  readonly property var stats: ({
    cpu: { usage: 41.2, temp: 45, power: 120, freq: 4895 },
    gpu: [{ usage: 6, memPct: 12.2, temp: 27, power: 35.6 }],
    net: { up: 1400, down: 118000000 },
    disks: { read: 2000, write: 0 },
    mem: { usedPct: 48.4, pressure: 3, swapTotal: 100, swapUsed: 25 }
  })

  function test_every_history_choice_has_a_definition() {
    L.catalog.history.metrics.forEach(function(key) {
      verify(M.info[key], key)
      verify(M.info[key].series.length > 0, key)
    })
  }
  function test_series_keys_are_what_the_collector_records() {
    var known = ["cpuUser", "cpuSystem", "cpuTemp", "cpuPower", "gpuUsage", "gpuMemory", "gpuTemp", "gpuPower",
                 "netDown", "netUp", "diskRead", "diskWrite", "memUsed", "memPressure", "swapUsed"]
    for (var key in M.info) M.info[key].series.forEach(function(s) { verify(known.indexOf(s.key) >= 0, s.key) })
  }
  function test_values() {
    compare(M.valueText(stats, "cpu.load", false), "41%")
    compare(M.valueText(stats, "gpu.temp", true), "81°")
    compare(M.valueText(stats, "gpu.power", false), "36W")
    compare(M.valueText(stats, "net", false), "↓ 118 MB/s  ↑ 1.4 KB/s")
    compare(M.valueText(stats, "disk", false), "R 2.0 KB/s  W 0 B/s")
    compare(M.valueText(stats, "mem.pressure", false), "3%")
    compare(M.valueText(stats, "swap", false), "25%")
  }
  function test_values_with_no_data_do_not_throw() {
    compare(M.valueText({}, "gpu.usage", false), "–")
    compare(M.valueText(null, "cpu.load", false), "–")
    compare(M.valueText({}, "net", false), "↓ –  ↑ –")
  }
  function test_sub_text_adds_context_to_load_graphs() {
    compare(M.subText(stats, "cpu.load", false), "4.9 GHz · 45° · 120W")
    compare(M.subText(stats, "gpu.usage", false), "36W · 27°")
    compare(M.subText(stats, "mem.used", false), "")
    compare(M.subText(null, "cpu.load", false), "– · – · –")
  }
  function test_percent_scale_is_fixed() {
    compare(M.scale("percent", [[5, 10]]), { min: 0, max: 100 })
  }
  function test_flat_zero_rate_still_has_a_range() {
    compare(M.scale("rate", [[0, 0]]), { min: 0, max: 1 })
    compare(M.scale("rate", []), { min: 0, max: 1 })
  }
  function test_rate_scale_follows_the_peak() {
    compare(M.scale("rate", [[0, 500], [900, null]]).max, 900)
  }
  function test_temperature_scale_stays_readable() {
    var s = M.scale("temp", [[40, 42]])
    verify(s.min <= 30 && s.max >= 60)
    compare(M.scale("temp", [[50, 96]]).max, 100)
  }
  function test_load_colors_escalate() {
    compare(M.level(10), "green")
    compare(M.level(70), "yellow")
    compare(M.level(95), "red")
    compare(M.level(null), "muted")
  }
}
