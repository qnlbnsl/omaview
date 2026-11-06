import QtQuick
import qs.Commons
import ".."
import "../../lib/metrics.js" as M
import "../../lib/format.js" as F

Column {
  id: root
  property var host
  readonly property var def: M.info[host.spec.metric]
  readonly property var history: (host.stats && host.stats.history) || ({})
  readonly property real graphHeight: ({ s: Style.space(38), m: Style.space(66), l: Style.space(116) })[host.spec.size]
  spacing: Style.space(5)

  CardHeader {
    theme: root.host.theme
    title: root.def.title
    value: M.valueText(root.host.stats, root.host.spec.metric, root.host.fahrenheit)
  }
  Graph {
    width: parent.width
    height: root.graphHeight
    theme: root.host.theme
    kind: root.def.kind
    stacked: !!root.def.stacked
    mirrored: !!root.def.mirrored
    series: root.def.series.map(function(s) {
      return { values: root.history[s.key] || [], color: root.host.theme.color(s.color) }
    })
  }
  Item {
    width: parent.width
    implicitHeight: age.implicitHeight
    Row {
      spacing: Style.space(8)
      Repeater {
        model: root.def.series.length > 1 ? root.def.series : []
        Row {
          required property var modelData
          spacing: Style.space(3)
          Rectangle {
            width: Style.space(7); height: width; radius: width / 2
            anchors.verticalCenter: parent.verticalCenter
            color: root.host.theme.color(modelData.color)
          }
          Label { theme: root.host.theme; dim: true; text: modelData.label; font.pixelSize: Style.font.caption }
        }
      }
      Label {
        visible: text !== ""
        theme: root.host.theme
        dim: true
        font.pixelSize: Style.font.caption
        text: M.subText(root.host.stats, root.host.spec.metric, root.host.fahrenheit)
      }
    }
    Label {
      id: age
      anchors.right: parent.right
      theme: root.host.theme
      dim: true
      text: "4 min"
      font.pixelSize: Style.font.caption
    }
  }
}
