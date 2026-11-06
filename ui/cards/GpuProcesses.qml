import QtQuick
import qs.Commons
import ".."
import "../../lib/format.js" as F

Column {
  id: root
  property var host
  readonly property var rows: (host.stats && host.stats.gpu && host.stats.gpu[0] && host.stats.gpu[0].processes) || []
  readonly property int count: ({ s: 3, m: 6, l: 12 })[host.spec.size]
  readonly property real typeWidth: Style.space(30)
  readonly property real useWidth: Style.space(36)
  readonly property real memWidth: Style.space(60)
  spacing: Style.space(2)

  component Line: Item {
    id: line
    property string name
    property string type
    property string use
    property string memory
    property bool dim: false
    width: root.width
    height: Style.space(19)
    Label {
      theme: root.host.theme
      dim: line.dim
      text: line.name
      anchors.left: parent.left
      anchors.right: typeLabel.left
      anchors.rightMargin: Style.space(6)
      anchors.verticalCenter: parent.verticalCenter
    }
    Label {
      id: typeLabel
      theme: root.host.theme
      dim: true
      text: line.type
      width: root.typeWidth
      horizontalAlignment: Text.AlignRight
      anchors.right: useLabel.left
      anchors.verticalCenter: parent.verticalCenter
    }
    Label {
      id: useLabel
      theme: root.host.theme
      dim: line.dim
      text: line.use
      width: root.useWidth
      horizontalAlignment: Text.AlignRight
      anchors.right: memLabel.left
      anchors.verticalCenter: parent.verticalCenter
    }
    Label {
      id: memLabel
      theme: root.host.theme
      dim: line.dim
      text: line.memory
      width: root.memWidth
      horizontalAlignment: Text.AlignRight
      anchors.right: parent.right
      anchors.verticalCenter: parent.verticalCenter
    }
  }

  CardHeader { theme: root.host.theme; title: "GPU processes" }
  Line { name: "Name"; type: "Type"; use: "GPU"; memory: "Memory"; dim: true }
  Repeater {
    model: root.rows.slice(0, root.count)
    Line {
      required property var modelData
      name: modelData.name + (modelData.count > 1 ? "  ×" + modelData.count : "")
        + (modelData.encode > 0 ? "  enc " + modelData.encode + "%" : "")
        + (modelData.decode > 0 ? "  dec " + modelData.decode + "%" : "")
      type: modelData.type
      use: F.percent(modelData.usage)
      memory: F.bytes(modelData.memory)
    }
  }
}
