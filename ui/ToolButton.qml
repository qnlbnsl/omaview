import QtQuick
import qs.Commons

Rectangle {
  id: root
  property var theme
  property string text
  signal clicked()

  implicitWidth: label.implicitWidth + Style.space(12)
  implicitHeight: label.implicitHeight + Style.space(6)
  radius: Style.space(5)
  color: mouse.containsMouse ? theme.track : theme.card

  Label {
    id: label
    theme: root.theme
    text: root.text
    anchors.centerIn: parent
  }
  MouseArea {
    id: mouse
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    onClicked: root.clicked()
  }
}
