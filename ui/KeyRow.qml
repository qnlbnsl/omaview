import QtQuick
import qs.Commons

// One label/value row, with an optional meter underneath.
Column {
  id: root
  property var theme
  property string label
  property string value
  property bool showMeter: false
  property real meter: 0
  property color meterColor: theme ? theme.foreground : "white"
  width: parent ? parent.width : 0
  spacing: Style.space(2)

  Item {
    width: parent.width
    implicitHeight: name.implicitHeight
    Label {
      id: name
      theme: root.theme
      dim: true
      text: root.label
      anchors.left: parent.left
      anchors.right: val.left
      anchors.rightMargin: Style.space(8)
    }
    Label {
      id: val
      theme: root.theme
      text: root.value
      anchors.right: parent.right
    }
  }
  Meter {
    visible: root.showMeter
    width: parent.width
    theme: root.theme
    value: root.meter
    fill: root.meterColor
  }
}
