import QtQuick
import qs.Commons
import ".."
import "../../lib/format.js" as F

Column {
  id: root
  property var host
  readonly property var mem: (host.stats && host.stats.mem) || ({})
  readonly property var parts: [
    { label: "Apps", value: mem.apps, color: "blue" }, { label: "Cache", value: mem.cache, color: "yellow" },
    { label: "Shared", value: mem.shared, color: "magenta" }, { label: "Free", value: mem.free, color: "green" }
  ]
  spacing: Style.space(4)

  CardHeader {
    theme: root.host.theme
    title: "Memory"
    value: F.bytes(root.mem.used) + " of " + F.bytes(root.mem.total)
  }
  Rectangle {
    width: parent.width
    height: Style.space(8)
    radius: height / 2
    clip: true
    color: root.host.theme.track
    Row {
      anchors.fill: parent
      Repeater {
        model: root.parts
        Rectangle {
          required property var modelData
          height: parent.height
          width: root.mem.total ? root.width * Math.max(0, modelData.value || 0) / root.mem.total : 0
          color: root.host.theme.color(modelData.color)
        }
      }
    }
  }
  Repeater {
    model: root.parts
    Item {
      required property var modelData
      width: root.width
      implicitHeight: row.implicitHeight
      KeyRow {
        id: row
        anchors.left: parent.left
        anchors.leftMargin: Style.space(12)
        anchors.right: parent.right
        width: undefined
        theme: root.host.theme
        label: modelData.label
        value: F.bytes(modelData.value)
      }
      Rectangle {
        width: Style.space(7); height: width; radius: width / 2
        anchors.verticalCenter: parent.verticalCenter
        color: root.host.theme.color(modelData.color)
      }
    }
  }
  KeyRow {
    theme: root.host.theme
    label: "Swap"
    value: F.bytes(root.mem.swapUsed) + " of " + F.bytes(root.mem.swapTotal)
    showMeter: true
    meter: root.mem.swapTotal ? 100 * root.mem.swapUsed / root.mem.swapTotal : 0
    meterColor: root.host.theme.color("cyan")
  }
}
