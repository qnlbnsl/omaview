import QtQuick
import qs.Commons
import ".."
import "../../lib/format.js" as F

Column {
  id: root
  property var host
  readonly property string metric: host.spec.metric
  readonly property int count: ({ s: 3, m: 5, l: 10 })[host.spec.size]
  readonly property var table: (host.stats && host.stats.processes && host.stats.processes[metric]) || []
  // Idle processes all read zero for disk, and listing them in arbitrary order says nothing.
  readonly property var shown: table.filter(function(r) { return metric !== "disk" || r.io > 0 }).slice(0, count)
  readonly property string field: metric === "disk" ? "io" : metric
  readonly property real peak: Math.max(1e-9, ...shown.map(function(r) { return r[field] || 0 }))
  spacing: Style.space(2)

  function valueFor(row) {
    if (metric === "cpu") return (row.cpu < 10 ? row.cpu.toFixed(1) : Math.round(row.cpu)) + "%"
    if (metric === "memory") return F.bytes(row.memory)
    return "R " + F.rate(row.read) + "  W " + F.rate(row.write)
  }

  CardHeader {
    theme: root.host.theme
    title: "Top processes"
    value: ({ cpu: "CPU", memory: "Memory", disk: "Disk" })[root.metric]
  }
  Repeater {
    model: root.shown
    Item {
      required property var modelData
      width: root.width
      height: Style.space(19)
      Rectangle {
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        height: parent.height - Style.space(3)
        width: parent.width * (modelData[root.field] || 0) / root.peak
        radius: Style.space(3)
        color: root.host.theme.grid
      }
      Label {
        theme: root.host.theme
        anchors.left: parent.left
        anchors.leftMargin: Style.space(4)
        anchors.right: procValue.left
        anchors.rightMargin: Style.space(8)
        anchors.verticalCenter: parent.verticalCenter
        text: modelData.name + (modelData.count > 1 ? "  ×" + modelData.count : "")
      }
      Label {
        id: procValue
        theme: root.host.theme
        anchors.right: parent.right
        anchors.rightMargin: Style.space(4)
        anchors.verticalCenter: parent.verticalCenter
        text: root.valueFor(modelData)
      }
    }
  }
  Label {
    visible: root.shown.length === 0
    theme: root.host.theme
    dim: true
    height: Style.space(19)
    text: root.metric === "disk" ? "No disk activity" : "No data yet"
  }
  // Holds the height steady while the first report sample is on its way.
  Item { width: 1; height: Math.max(0, root.count - Math.max(1, root.shown.length)) * Style.space(21) }
}
