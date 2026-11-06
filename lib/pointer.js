.pragma library

// The section whose rectangle holds the point, or "" for none.
function sectionAt(x, y, rects) {
  for (var i = rects.length - 1; i >= 0; i--) {
    var r = rects[i]
    if (x >= r.x && x < r.x + r.width && y >= r.y && y < r.y + r.height) return r.id
  }
  return ""
}

// `hyprctl cursorpos -j` output as { x, y }, or null if it can't be read.
function parseCursor(text) {
  try {
    var position = JSON.parse(text)
    if (typeof position.x === "number" && typeof position.y === "number") return { x: position.x, y: position.y }
  } catch (e) {}
  return null
}

// Moving less than this between two readings counts as stopping.
var STILL_PX = 8

// Follows the pointer inside a report to tell someone heading for a card from someone just
// crossing it. Pass null to start. `settled` means it stopped, and `through` means it kept
// moving for limitMs without stopping.
function trackPass(tracker, x, y, now, limitMs) {
  if (!tracker) return { startedAt: now, x: x, y: y, settled: false, through: false }
  if (tracker.settled || tracker.through) return tracker
  var moved = Math.sqrt(Math.pow(x - tracker.x, 2) + Math.pow(y - tracker.y, 2))
  return {
    startedAt: tracker.startedAt,
    x: x,
    y: y,
    settled: moved < STILL_PX,
    through: moved >= STILL_PX && now - tracker.startedAt >= limitMs
  }
}
