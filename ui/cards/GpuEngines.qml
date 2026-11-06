import QtQuick
import qs.Commons
import ".."
import "../../lib/metrics.js" as M
import "../../lib/format.js" as F

Column {
  id: root
  property var host
  readonly property var engines: (host.stats && host.stats.gpu && host.stats.gpu[0] && host.stats.gpu[0].engines) || ({})
  spacing: Style.space(4)

  CardHeader { theme: root.host.theme; title: "Engines" }
  Repeater {
    model: [
      { key: "graphics", label: "3D and compute" }, { key: "encode", label: "Encode" }, { key: "decode", label: "Decode" },
      { key: "jpeg", label: "JPEG" }, { key: "opticalFlow", label: "Optical flow" }
    ]
    KeyRow {
      required property var modelData
      theme: root.host.theme
      label: modelData.label
      value: F.percent(root.engines[modelData.key])
      showMeter: true
      meter: root.engines[modelData.key] || 0
      meterColor: root.host.theme.color(modelData.key === "graphics" ? "green" : "blue")
    }
  }
}
