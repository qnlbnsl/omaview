import QtQuick
import qs.Commons
import ".."
import "../../lib/metrics.js" as M
import "../../lib/format.js" as F

Column {
  id: root
  property var host
  readonly property var stats: host.stats || ({})
  readonly property var cpu: stats.cpu || ({})
  readonly property var gpu: (stats.gpu && stats.gpu[0]) || ({})
  readonly property var mem: stats.mem || ({})
  readonly property bool f: host.fahrenheit
  spacing: Style.space(8)

  readonly property var rings: {
    switch (host.spec.metric) {
    case "gpu": return [
      { label: "Load", value: gpu.usage, text: F.percent(gpu.usage) },
      { label: "Memory", value: gpu.memPct, text: F.percent(gpu.memPct) },
      { label: "Temp", value: gpu.temp, text: F.temp(gpu.temp, f) },
      { label: "Clock", value: gpu.clockMax ? 100 * gpu.clock / gpu.clockMax : 0, text: gpu.clock === undefined || gpu.clock === null ? F.NONE : (gpu.clock / 1000).toFixed(1) + "G", color: "blue" }]
    case "mem": return [
      { label: "Pressure", value: mem.pressure, text: F.percent(mem.pressure) },
      { label: "Memory", value: mem.usedPct, text: F.percent(mem.usedPct) },
      { label: "Swap", value: mem.swapTotal ? 100 * mem.swapUsed / mem.swapTotal : 0, text: F.percent(mem.swapTotal ? 100 * mem.swapUsed / mem.swapTotal : null) }]
    default: return [
      { label: "Load", value: cpu.usage, text: F.percent(cpu.usage) },
      { label: "Temp", value: cpu.temp, text: F.temp(cpu.temp, f) },
      { label: "Power", value: cpu.power ? cpu.power / 2.5 : 0, text: F.watts(cpu.power), color: "yellow" }]
    }
  }

  CardHeader {
    visible: root.host.spec.metric === "gpu"
    theme: root.host.theme
    title: root.gpu.name || "GPU"
    value: F.watts(root.gpu.power) + (root.gpu.powerLimit ? " of " + root.gpu.powerLimit + "W" : "")
  }
  Row {
    anchors.horizontalCenter: parent.horizontalCenter
    spacing: Style.space(12)
    Repeater {
      model: root.rings
      Ring {
        required property var modelData
        theme: root.host.theme
        label: modelData.label
        text: modelData.text
        value: modelData.value === undefined || modelData.value === null ? 0 : modelData.value
        fill: root.host.theme.color(modelData.color || M.level(modelData.value))
      }
    }
  }
  Label {
    visible: root.host.spec.metric === "gpu"
    width: parent.width
    horizontalAlignment: Text.AlignHCenter
    theme: root.host.theme
    dim: true
    font.pixelSize: Style.font.caption
    // Not every GPU reports all of these, so only show what this one has.
    text: {
      var gpu = root.gpu
      var parts = []
      if (gpu.memUsed !== undefined && gpu.memUsed !== null)
        parts.push("VRAM " + F.bytes(gpu.memUsed) + (gpu.memTotal ? " of " + F.bytes(gpu.memTotal) : ""))
      if (gpu.fan !== undefined && gpu.fan !== null) parts.push("Fan " + F.percent(gpu.fan))
      if (gpu.pstate !== undefined && gpu.pstate !== null) parts.push("P" + gpu.pstate)
      return parts.join("  ·  ")
    }
  }
}
