import QtQuick
import qs.Commons
import ".."
import "../../lib/format.js" as F

Column {
  id: root
  property var host
  readonly property var cpu: (host.stats && host.stats.cpu) || ({})
  readonly property var load: cpu.load || []
  spacing: Style.space(3)

  KeyRow {
    theme: root.host.theme
    label: "Load average"
    value: root.load.length ? root.load.map(function(v) { return v.toFixed(2) }).join("  ") : F.NONE
  }
  KeyRow {
    theme: root.host.theme
    label: "Uptime"
    value: F.duration(root.cpu.uptime)
  }
}
