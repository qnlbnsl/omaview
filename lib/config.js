.pragma library

var defaults = {
  openDelayMs: 300,
  systemOpenDelayMs: 500,
  closeOnPassThrough: true,
  passThroughMs: 400
}

var MAX_DELAY_MS = 5000

function validDelay(value) { return typeof value === "number" && value >= 0 && value <= MAX_DELAY_MS }

// The settings from config.json. Anything missing or invalid falls back to its default.
function parse(text) {
  var read = {}
  try {
    var parsed = JSON.parse(text)
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) read = parsed
  } catch (e) {}
  return {
    openDelayMs: validDelay(read.openDelayMs) ? read.openDelayMs : defaults.openDelayMs,
    systemOpenDelayMs: validDelay(read.systemOpenDelayMs) ? read.systemOpenDelayMs : defaults.systemOpenDelayMs,
    closeOnPassThrough: typeof read.closeOnPassThrough === "boolean" ? read.closeOnPassThrough : defaults.closeOnPassThrough,
    passThroughMs: validDelay(read.passThroughMs) ? read.passThroughMs : defaults.passThroughMs
  }
}
