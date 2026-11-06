import QtQuick
import qs.Commons
import qs.Ui

WidgetButton {
  id: root
  property bool highlighted: false
  horizontalMargin: 7

  Rectangle {
    anchors.fill: parent
    anchors.topMargin: Style.space(3)
    anchors.bottomMargin: Style.space(3)
    z: -1
    radius: Style.space(5)
    color: root.foreground
    opacity: root.highlighted ? 0.14 : 0
    Behavior on opacity { NumberAnimation { duration: 120 } }
  }
}
