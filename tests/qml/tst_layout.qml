import QtQuick
import QtTest
import "../../lib/layout.js" as L

TestCase {
  name: "Layout"

  function names(columns) { return columns.map(function(c) { return c.map(function(x) { return x.card }) }) }

  function test_defaults_cover_all_three_reports() {
    var r = L.resolve(null)
    verify(r.cpu.length === 1)
    verify(r.gpu.length === 1)
    compare(r.system.length, 2)
    compare(r.cpu[0][1].card, "coreGrid")
  }
  function test_saved_report_replaces_only_that_report() {
    var r = L.resolve({ cpu: [[{ card: "coreGrid" }]] })
    compare(names(r.cpu), [["coreGrid"]])
    compare(r.system.length, 2)
  }
  // The shell hands settings over as Qt sequences, which fail Array.isArray but serialize fine.
  function test_saved_layouts_need_not_be_plain_js_arrays() {
    var sequence = { toJSON: function() { return [[{ card: "coreGrid" }]] } }
    compare(names(L.resolve({ cpu: sequence }).cpu), [["coreGrid"]])
  }
  function test_metric_labels_are_readable() {
    compare(L.metricLabel({ card: "history", metric: "cpu.load" }), "CPU load")
    compare(L.metricLabel({ card: "processes", metric: "memory" }), "Memory")
    compare(L.metricLabel({ card: "rings", metric: "gpu" }), "GPU")
    compare(L.metricLabel({ card: "coreGrid" }), "")
  }
  function test_unknown_cards_and_garbage_are_dropped() {
    var r = L.resolve({ cpu: [[{ card: "nope" }, 7, { card: "coreGrid" }]], gpu: "bad" })
    compare(names(r.cpu), [["coreGrid"]])
    verify(r.gpu[0].length > 1)
  }
  function test_invalid_metric_and_size_fall_back() {
    var c = L.resolve({ cpu: [[{ card: "history", metric: "nope", size: "xl" }]] }).cpu[0][0]
    compare(c.metric, "cpu.load")
    compare(c.size, "m")
  }
  function test_all_columns_empty_stays_editable() {
    compare(L.resolve({ cpu: [[]] }).cpu, [[]])
    compare(L.remove([[{ card: "coreGrid" }]], 0, 0), [[]])
  }
  function test_overrides_store_only_what_differs() {
    var r = L.resolve(null)
    compare(L.overrides(r), {})
    r.cpu = [[{ card: "coreGrid", size: "m" }]]
    compare(Object.keys(L.overrides(r)), ["cpu"])
  }
  function test_move_within_column() {
    var cols = [[{ card: "a" }, { card: "b" }, { card: "c" }]]
    compare(names(L.moveVertical(cols, 0, 0, 1)), [["b", "a", "c"]])
    compare(names(L.moveVertical(cols, 0, 0, -1)), [["a", "b", "c"]])
    compare(names(cols), [["a", "b", "c"]])
  }
  function test_move_across_columns_creates_and_removes_columns() {
    var one = [[{ card: "a" }, { card: "b" }]]
    compare(names(L.moveAcross(one, 0, 0, 1)), [["b"], ["a"]])
    compare(names(L.moveAcross(one, 0, 0, -1)), [["a", "b"]])
    compare(names(L.moveAcross([[{ card: "a" }], [{ card: "b" }]], 1, 0, -1)), [["a", "b"]])
    var full = [[{ card: "a" }], [{ card: "b" }], [{ card: "c" }]]
    compare(names(L.moveAcross(full, 2, 0, 1)), [["a"], ["b"], ["c"]])
  }
  function test_cycle_size() {
    var cols = [[{ card: "history", metric: "cpu.load", size: "l" }]]
    compare(L.cycleSize(cols, 0, 0)[0][0].size, "s")
    compare(cols[0][0].size, "l")
  }
  function test_size_cycles_only_when_card_supports_it() {
    var cols = [[{ card: "coreGrid", size: "m" }]]
    compare(L.cycleSize(cols, 0, 0)[0][0].size, "m")
  }
  function test_cycle_metric_wraps() {
    var metrics = L.catalog.processes.metrics
    var cols = [[{ card: "processes", metric: metrics[metrics.length - 1], size: "m" }]]
    compare(L.cycleMetric(cols, 0, 0)[0][0].metric, metrics[0])
  }
  function test_add_appends_a_valid_card() {
    var added = L.add([[]], 0, "history")[0][0]
    compare(added.card, "history")
    compare(added.metric, "cpu.load")
    compare(added.size, "m")
  }
  function test_every_default_card_is_in_the_catalog() {
    var r = L.resolve(null)
    ;["cpu", "gpu", "system"].forEach(function(report) {
      r[report].forEach(function(col) { col.forEach(function(c) { verify(L.catalog[c.card], c.card) }) })
    })
  }
}
