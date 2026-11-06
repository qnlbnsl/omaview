import QtQuick
import qs.Commons
import ".."
import "../../lib/metrics.js" as M
import "../../lib/format.js" as F

Column {
  id: root
  property var host
  readonly property var list: (host.stats && host.stats.sensors && host.stats.sensors.temps) || []
  readonly property bool hasContent: list.length > 0
  spacing: Style.space(3)

  CardHeader { theme: root.host.theme; title: "Temperatures" }
  Repeater {
    model: root.list
    KeyRow {
      required property var modelData
      theme: root.host.theme
      label: modelData.name.replace(/_/g, " ")
      value: F.temp(modelData.value, root.host.fahrenheit)
      showMeter: true
      meter: modelData.value
      meterColor: root.host.theme.color(M.level(modelData.value))
    }
  }
}
