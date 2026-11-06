.pragma library

var NONE = "–"

function missing(value) { return value === null || value === undefined || isNaN(value) }

function percent(value) { return missing(value) ? NONE : Math.round(value) + "%" }

function temp(celsius, fahrenheit) {
  if (missing(celsius)) return NONE
  return Math.round(fahrenheit ? celsius * 9 / 5 + 32 : celsius) + "°"
}

function watts(value) { return missing(value) ? NONE : Math.round(value) + "W" }

function scaled(value, base, units) {
  var i = 0
  while (value >= base && i < units.length - 1) { value /= base; i++ }
  // Reserve one decimal for small numbers, and never for plain bytes.
  var text = i === 0 || value >= 100 ? String(Math.round(value)) : value.toFixed(1)
  return text + " " + units[i]
}

function bytes(value) {
  return missing(value) ? NONE : scaled(value, 1024, ["B", "KB", "MB", "GB", "TB", "PB"])
}

function rate(value) {
  return missing(value) ? NONE : scaled(value, 1000, ["B/s", "KB/s", "MB/s", "GB/s"])
}

function duration(seconds) {
  if (missing(seconds)) return NONE
  var days = Math.floor(seconds / 86400)
  var hours = Math.floor(seconds % 86400 / 3600)
  var minutes = Math.floor(seconds % 3600 / 60)
  if (days > 0) return days + "d " + hours + "h"
  if (hours > 0) return hours + "h " + minutes + "m"
  return minutes + "m"
}

function clock(mhz) {
  if (missing(mhz)) return NONE
  return mhz >= 1000 ? (mhz / 1000).toFixed(1) + " GHz" : Math.round(mhz) + " MHz"
}

function barSection(label, data, fahrenheit) {
  var d = data || {}
  return label + " " + percent(d.usage) + " " + temp(d.temp, fahrenheit) + " " + watts(d.power)
}

function barNetwork(net) {
  var n = net || {}
  return "↑ " + rate(n.up) + " ↓ " + rate(n.down)
}

function shellQuote(value) { return "'" + String(value).replace(/'/g, "'\\''") + "'" }
