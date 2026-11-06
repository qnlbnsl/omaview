import QtQuick
import QtTest
import "../../lib/config.js" as C

TestCase {
  name: "config"

  function test_missing_or_broken_files_use_the_defaults() {
    compare(C.parse(""), C.defaults)
    compare(C.parse("not json"), C.defaults)
    compare(C.parse("[1, 2]"), C.defaults)
  }

  function test_a_partial_file_keeps_the_other_defaults() {
    var config = C.parse('{ "closeOnPassThrough": false }')
    compare(config.closeOnPassThrough, false)
    compare(config.openDelayMs, C.defaults.openDelayMs)
  }

  function test_reads_every_setting() {
    var config = C.parse('{ "openDelayMs": 100, "systemOpenDelayMs": 200, "closeOnPassThrough": false, "passThroughMs": 300 }')
    compare(config, { openDelayMs: 100, systemOpenDelayMs: 200, closeOnPassThrough: false, passThroughMs: 300 })
  }

  function test_values_of_the_wrong_type_or_range_are_ignored() {
    var config = C.parse('{ "openDelayMs": "fast", "systemOpenDelayMs": -1, "closeOnPassThrough": "no", "passThroughMs": 999999 }')
    compare(config, C.defaults)
  }
}
