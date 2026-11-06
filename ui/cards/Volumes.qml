import QtQuick
import qs.Commons
import ".."
import "../../lib/metrics.js" as M
import "../../lib/format.js" as F

Column {
  id: root
  property var host
  readonly property var disks: (host.stats && host.stats.disks) || ({})
  readonly property var volumes: disks.volumes || []
  readonly property var names: Object.keys(disks.perDisk || {}).sort()
  spacing: Style.space(5)

  CardHeader { theme: root.host.theme; title: "Disks" }
  Repeater {
    model: root.volumes
    KeyRow {
      required property var modelData
      theme: root.host.theme
      label: modelData.mount
      value: F.bytes(modelData.free) + " free of " + F.bytes(modelData.total)
      showMeter: true
      meter: modelData.usedPct
      meterColor: root.host.theme.color(M.level(modelData.usedPct))
    }
  }
  Repeater {
    model: root.names
    KeyRow {
      required property string modelData
      theme: root.host.theme
      label: (root.disks.models && root.disks.models[modelData]) || modelData
      value: "R " + F.rate(root.disks.perDisk[modelData].read) + "  W " + F.rate(root.disks.perDisk[modelData].write)
    }
  }
}
