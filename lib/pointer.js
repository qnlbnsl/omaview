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
