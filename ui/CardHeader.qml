import QtQuick
import qs.Commons

Item {
  id: root
  property var theme
  property string title
  property string value
  width: parent.width
  implicitHeight: titleLabel.implicitHeight

  Label {
    id: titleLabel
    theme: root.theme
    text: root.title
    font.pixelSize: Style.font.body
    font.weight: Font.DemiBold
    anchors.left: parent.left
    anchors.right: valueLabel.left
    anchors.rightMargin: Style.space(8)
  }
  Label {
    id: valueLabel
    theme: root.theme
    text: root.value
    anchors.right: parent.right
    anchors.baseline: titleLabel.baseline
  }
}
