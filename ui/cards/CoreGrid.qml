import QtQuick
import qs.Commons
import ".."
import "../../lib/metrics.js" as M
import "../../lib/format.js" as F

Column {
  id: root
  property var host
  readonly property var cpu: (host.stats && host.stats.cpu) || ({})
  readonly property var cores: cpu.cores || []
  readonly property var pairs: cpu.threads || []
  readonly property int rows: pairs.length && pairs[0].length > 1 ? 2 : 1
  readonly property real cellGap: Style.space(2)
  readonly property real cellWidth: pairs.length ? (width - cellGap * (pairs.length - 1)) / pairs.length : 0
  spacing: Style.space(5)

  CardHeader {
    theme: root.host.theme
    title: "Cores"
    value: root.pairs.length + " cores · " + root.cores.length + " threads"
  }
  Repeater {
    model: root.rows
    Row {
      required property int index
      readonly property int rowIndex: index
      spacing: root.cellGap
      Repeater {
        model: root.pairs
        Rectangle {
          required property var modelData
          readonly property real load: root.cores[modelData[parent.rowIndex]] || 0
          width: root.cellWidth
          height: Style.space(20)
          radius: Style.space(2)
          color: root.host.theme.track
          Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: parent.height * Math.min(100, parent.load) / 100
            radius: parent.radius
            color: root.host.theme.color(M.level(parent.load))
            Behavior on height { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
          }
        }
      }
    }
  }
}
