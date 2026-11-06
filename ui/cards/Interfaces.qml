import QtQuick
import qs.Commons
import ".."

Column {
  id: root
  property var host
  readonly property var list: (host.stats && host.stats.net && host.stats.net.interfaces) || []
  readonly property bool hasContent: list.length > 0
  spacing: Style.space(3)

  CardHeader { theme: root.host.theme; title: "Interfaces" }
  Repeater {
    model: root.list
    KeyRow {
      required property var modelData
      theme: root.host.theme
      label: modelData.name + "  ·  " + (modelData.kind === "wifi" ? "Wi-Fi" : "Ethernet")
      value: modelData.ip || "No address"
    }
  }
}
