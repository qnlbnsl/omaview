import QtQuick
import QtTest
import "../../lib/pointer.js" as P

TestCase {
  name: "pointer"

  readonly property var rects: [
    { id: "cpu", x: 100, y: 0, width: 50, height: 26 },
    { id: "gpu", x: 150, y: 0, width: 50, height: 26 }
  ]

  function test_finds_the_section_under_the_pointer() {
    compare(P.sectionAt(120, 10, rects), "cpu")
    compare(P.sectionAt(175, 10, rects), "gpu")
  }

  function test_a_shared_edge_belongs_to_the_next_section() {
    compare(P.sectionAt(150, 10, rects), "gpu")
  }

  function test_outside_every_section_is_empty() {
    compare(P.sectionAt(99, 10, rects), "")
    compare(P.sectionAt(200, 10, rects), "")
    compare(P.sectionAt(120, 26, rects), "")
  }

  function test_reads_hyprctl_output() {
    compare(P.parseCursor('{"x": 3553, "y": 13}'), { x: 3553, y: 13 })
  }

  function test_bad_hyprctl_output_is_null() {
    compare(P.parseCursor("not json"), null)
    compare(P.parseCursor('{"x": "a", "y": 1}'), null)
  }

  function test_stopping_settles() {
    var tracker = P.trackPass(null, 100, 100, 0, 400)
    tracker = P.trackPass(tracker, 100, 180, 80, 400)
    verify(!tracker.settled && !tracker.through)
    tracker = P.trackPass(tracker, 102, 183, 160, 400)
    verify(tracker.settled && !tracker.through)
  }

  function test_moving_past_the_limit_is_a_pass_through() {
    var tracker = P.trackPass(null, 100, 100, 0, 400)
    tracker = P.trackPass(tracker, 100, 200, 200, 400)
    verify(!tracker.through)
    tracker = P.trackPass(tracker, 100, 300, 400, 400)
    verify(tracker.through && !tracker.settled)
  }

  function test_settling_is_final() {
    var tracker = P.trackPass(null, 100, 100, 0, 400)
    tracker = P.trackPass(tracker, 100, 100, 80, 400)
    tracker = P.trackPass(tracker, 100, 900, 2000, 400)
    verify(tracker.settled && !tracker.through)
  }
}
