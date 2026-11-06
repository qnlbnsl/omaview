import QtQuick
import qs.Commons
import "../lib/layout.js" as L

Rectangle {
  id: root

  property var spec
  property var stats
  property var theme
  property bool fahrenheit
  property bool editing
  signal action(string name)

  readonly property var entry: spec ? L.catalog[spec.card] : null
  readonly property bool hasContent: !loader.item || loader.item.hasContent !== false

  visible: editing || hasContent
  width: parent ? parent.width : 0
  implicitHeight: body.implicitHeight + Style.space(20)
  radius: Style.space(8)
  color: theme.card

  Column {
    id: body
    x: Style.space(10)
    y: Style.space(10)
    width: parent.width - Style.space(20)
    spacing: Style.space(6)

    Row {
      visible: root.editing
      width: parent.width
      spacing: Style.space(3)
      layoutDirection: Qt.RightToLeft
      ToolButton { theme: root.theme; text: "✕"; onClicked: root.action("remove") }
      ToolButton { theme: root.theme; text: "→"; onClicked: root.action("right") }
      ToolButton { theme: root.theme; text: "←"; onClicked: root.action("left") }
      ToolButton { theme: root.theme; text: "↓"; onClicked: root.action("down") }
      ToolButton { theme: root.theme; text: "↑"; onClicked: root.action("up") }
      ToolButton {
        theme: root.theme
        visible: !!root.entry && !!root.entry.sizes
        text: root.spec ? root.spec.size.toUpperCase() : ""
        onClicked: root.action("size")
      }
      ToolButton {
        theme: root.theme
        visible: !!root.entry && !!root.entry.metrics
        text: root.spec && root.spec.metric ? L.metricLabel(root.spec) + " ›" : ""
        onClicked: root.action("metric")
      }
    }

    Loader {
      id: loader
      width: parent.width
      Component.onCompleted: {
        var name = root.spec.card.charAt(0).toUpperCase() + root.spec.card.slice(1)
        setSource("cards/" + name + ".qml", { host: root })
      }
    }
  }
}
