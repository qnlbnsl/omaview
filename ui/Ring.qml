import QtQuick
import qs.Commons

Item {
  id: root
  property var theme
  property real value: 0
  property string text
  property string label
  property color fill: theme ? theme.foreground : "white"
  property real size: Style.space(62)
  width: size
  height: size + caption.implicitHeight + Style.space(3)

  Canvas {
    id: canvas
    width: root.size
    height: root.size
    onPaint: {
      var ctx = getContext("2d")
      ctx.reset()
      var line = Math.max(3, root.size * 0.085)
      var r = (root.size - line) / 2
      var c = root.size / 2
      var start = Math.PI * 0.75
      var sweep = Math.PI * 1.5
      ctx.lineWidth = line
      ctx.lineCap = "round"
      ctx.strokeStyle = root.theme ? root.theme.track : "gray"
      ctx.beginPath()
      ctx.arc(c, c, r, start, start + sweep)
      ctx.stroke()
      var fraction = Math.max(0, Math.min(1, (root.value || 0) / 100))
      if (fraction > 0) {
        ctx.strokeStyle = root.fill
        ctx.beginPath()
        ctx.arc(c, c, r, start, start + sweep * fraction)
        ctx.stroke()
      }
    }
  }
  onValueChanged: canvas.requestPaint()
  onFillChanged: canvas.requestPaint()

  Label {
    theme: root.theme
    text: root.text
    anchors.centerIn: canvas
    width: root.size - Style.space(14)
    horizontalAlignment: Text.AlignHCenter
    font.pixelSize: Style.font.body
    font.weight: Font.DemiBold
  }
  Label {
    id: caption
    theme: root.theme
    dim: true
    text: root.label
    anchors.top: canvas.bottom
    anchors.topMargin: Style.space(1)
    width: root.size
    horizontalAlignment: Text.AlignHCenter
    font.pixelSize: Style.font.caption
  }
}
