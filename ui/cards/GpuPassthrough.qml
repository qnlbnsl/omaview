import QtQuick
import qs.Commons
import ".."

Column {
  id: root
  property var host
  readonly property var devices: (host.stats && host.stats.gpuPassthrough) || []
  readonly property bool hasContent: devices.length > 0
  spacing: Style.space(3)

  Repeater {
    model: root.devices
    KeyRow {
      required property var modelData
      theme: root.host.theme
      label: modelData.name
      value: "Passed through to a VM"
    }
  }
}
