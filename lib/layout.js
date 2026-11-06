.pragma library
.import "metrics.js" as M

// Everything a report can show. `metrics` are the choices the builder cycles through;
// `sizes` is false for cards whose height comes from their content.
var HISTORY = ["cpu.load", "cpu.temp", "cpu.power", "gpu.usage", "gpu.memory", "gpu.temp", "gpu.power",
               "net", "disk", "mem.used", "mem.pressure", "swap"]

var catalog = {
  history: { label: "History graph", metrics: HISTORY, sizes: true },
  rings: { label: "Rings", metrics: ["gpu", "mem", "cpu"], sizes: false },
  coreGrid: { label: "CPU cores", sizes: false },
  cpuStats: { label: "Load and uptime", sizes: false },
  processes: { label: "Top processes", metrics: ["cpu", "memory", "disk"], sizes: true },
  gpuEngines: { label: "GPU engines", sizes: false },
  gpuProcesses: { label: "GPU processes", sizes: true },
  gpuPassthrough: { label: "Passed-through GPUs", sizes: false },
  interfaces: { label: "Network interfaces", sizes: false },
  volumes: { label: "Disk space", sizes: false },
  memBreakdown: { label: "Memory and swap", sizes: false },
  temps: { label: "Temperature sensors", sizes: false },
  fans: { label: "Fans", sizes: false }
}

var SIZES = ["s", "m", "l"]
var MAX_COLUMNS = 3
var REPORTS = ["cpu", "gpu", "system"]

function make(card, metric, size) {
  var out = { card: card, size: size || "m" }
  if (metric) out.metric = metric
  return out
}

function defaults() {
  return {
    cpu: [[make("history", "cpu.load"), make("coreGrid"), make("processes", "cpu"), make("cpuStats")]],
    gpu: [[make("rings", "gpu"), make("history", "gpu.usage"), make("gpuEngines"), make("gpuProcesses"), make("gpuPassthrough")]],
    system: [
      [make("history", "net"), make("interfaces"), make("volumes"), make("history", "disk"), make("processes", "disk")],
      [make("rings", "mem"), make("memBreakdown"), make("processes", "memory"), make("temps"), make("fans")]
    ]
  }
}

function clean(item) {
  if (!item || typeof item !== "object") return null
  var entry = catalog[item.card]
  if (!entry) return null
  var metric = entry.metrics ? (entry.metrics.indexOf(item.metric) >= 0 ? item.metric : entry.metrics[0]) : null
  return make(item.card, metric, SIZES.indexOf(item.size) >= 0 ? item.size : "m")
}

function cleanColumns(columns) {
  if (!Array.isArray(columns) || columns.length === 0) return null
  var out = []
  for (var i = 0; i < columns.length && out.length < MAX_COLUMNS; i++) {
    if (!Array.isArray(columns[i])) continue
    var cards = columns[i].map(clean).filter(function(c) { return c !== null })
    if (cards.length > 0) out.push(cards)
  }
  return out.length > 0 ? out : [[]]
}

function resolve(saved) {
  var out = defaults()
  // Settings arrive as Qt sequences, which fail Array.isArray until copied into plain JS.
  var plain = saved ? JSON.parse(JSON.stringify(saved)) : null
  REPORTS.forEach(function(report) {
    var columns = plain ? cleanColumns(plain[report]) : null
    if (columns) out[report] = columns
  })
  return out
}

// Only customised reports are stored, so improved defaults still reach the others.
function overrides(layouts) {
  var base = defaults()
  var out = {}
  REPORTS.forEach(function(report) {
    if (JSON.stringify(layouts[report]) !== JSON.stringify(base[report])) out[report] = layouts[report]
  })
  return out
}

function copy(columns) { return JSON.parse(JSON.stringify(columns)) }

function compact(columns) {
  var out = columns.filter(function(c) { return c.length > 0 })
  return out.length > 0 ? out : [[]]
}

function moveVertical(columns, col, index, delta) {
  var out = copy(columns)
  var target = index + delta
  if (target < 0 || target >= out[col].length) return out
  out[col].splice(target, 0, out[col].splice(index, 1)[0])
  return out
}

function moveAcross(columns, col, index, delta) {
  var out = copy(columns)
  var target = col + delta
  if (target < 0) return out
  // Moving right off the edge opens a new column, unless that would just move a lone card.
  if (target >= out.length) {
    if (out.length >= MAX_COLUMNS || out[col].length < 2) return out
    out.push([])
  }
  out[target].push(out[col].splice(index, 1)[0])
  return compact(out)
}

function cycleSize(columns, col, index) {
  var out = copy(columns)
  var item = out[col][index]
  if (catalog[item.card].sizes) item.size = SIZES[(SIZES.indexOf(item.size) + 1) % SIZES.length]
  return out
}

function cycleMetric(columns, col, index) {
  var out = copy(columns)
  var item = out[col][index]
  var metrics = catalog[item.card].metrics
  if (metrics) item.metric = metrics[(metrics.indexOf(item.metric) + 1) % metrics.length]
  return out
}

function remove(columns, col, index) {
  var out = copy(columns)
  out[col].splice(index, 1)
  return compact(out)
}

function add(columns, col, card) {
  var out = copy(columns)
  var metrics = catalog[card].metrics
  out[col].push(make(card, metrics ? metrics[0] : null))
  return out
}

function metricLabel(item) {
  if (!item.metric) return ""
  if (item.card === "history") return M.info[item.metric].title
  return ({ cpu: "CPU", gpu: "GPU", mem: "Memory", memory: "Memory", disk: "Disk" })[item.metric] || item.metric
}
