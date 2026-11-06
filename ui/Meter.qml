import QtQuick
import qs.Commons

Rectangle {
  id: root
  property var theme
  property real value: 0
  property color fill: theme ? theme.foreground : "white"
  implicitHeight: Style.space(5)
  radius: height / 2
  color: theme ? theme.track : "gray"

  Rectangle {
    width: root.width * Math.max(0, Math.min(100, root.value || 0)) / 100
    height: parent.height
    radius: parent.radius
    color: root.fill
    Behavior on width { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
  }
}
