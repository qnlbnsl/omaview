import QtQuick
import qs.Commons
import ".."

Column {
  id: root
  property var host
  readonly property var list: (host.stats && host.stats.sensors && host.stats.sensors.fans) || []
  readonly property bool hasContent: list.length > 0
  spacing: Style.space(3)

  CardHeader { theme: root.host.theme; title: "Fans" }
  Repeater {
    model: root.list
    KeyRow {
      required property var modelData
      theme: root.host.theme
      label: modelData.name.replace(/_/g, " ")
      value: modelData.rpm + " RPM"
    }
  }
}
