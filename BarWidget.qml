import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import qs.Commons
import qs.Ui
import "ui"
import "lib/format.js" as F
import "lib/layout.js" as L

BarWidget {
  id: root
  moduleName: "io.github.qnlbnsl.omaview"

  readonly property bool fahrenheit: setting("temperatureUnit", "Celsius") === "Fahrenheit"
  readonly property bool mock: setting("mock", false) === true
  readonly property string socketPath: (Quickshell.env("XDG_RUNTIME_DIR") || "/tmp") + (mock ? "/omaview-mock.sock" : "/omaview.sock")

  // Latest message for the bar text, and latest full message for the reports.
  property var live: ({})
  property var detail: ({})

  property string activeReport: ""
  property var draft: null
  property var localLayouts: null
  readonly property bool editing: draft !== null
  readonly property var layouts: localLayouts || L.resolve(setting("layouts", null))

  property Theme theme: Theme { fontFamily: root.bar ? root.bar.fontFamily : Style.font.family }

  readonly property string hoveredSection: cpuButton.tooltipHovered ? "cpu"
    : gpuButton.tooltipHovered ? "gpu" : systemButton.tooltipHovered ? "system" : ""
  readonly property bool popupHovered: cpuPopup.containsMouse || gpuPopup.containsMouse || systemPopup.containsMouse

  onHoveredSectionChanged: updateHover()
  onPopupHoveredChanged: updateHover()
  onSettingsChanged: localLayouts = null
  onSocketPathChanged: {
    collector.running = false
    socket.connected = false
  }

  onActiveReportChanged: {
    syncDetail()
    if (activeReport !== "") theme.reload()
  }

  function updateHover() {
    if (editing) return
    if (hoveredSection !== "") {
      closeTimer.stop()
      if (activeReport === "") openTimer.restart()
      else if (!popupHovered) activeReport = hoveredSection
      return
    }
    openTimer.stop()
    if (popupHovered) closeTimer.stop()
    else if (activeReport !== "") closeTimer.restart()
  }

  function openReport(id) {
    closeTimer.stop()
    openTimer.stop()
    saveDraft()
    activeReport = id
  }

  function closeReport(id) {
    if (activeReport !== id) return
    saveDraft()
    activeReport = ""
  }

  function beginEdit() { draft = JSON.parse(JSON.stringify(layouts[activeReport])) }

  function saveDraft() {
    if (draft === null || activeReport === "") return
    var next = JSON.parse(JSON.stringify(layouts))
    next[activeReport] = draft
    draft = null
    localLayouts = next
    if (bar) bar.run("omarchy bar set " + moduleName + " layouts " + F.shellQuote(JSON.stringify(L.overrides(next))) + " --json")
    updateHover()
  }

  function syncDetail() {
    if (!socket.connected) return
    socket.write(activeReport !== "" ? "detail on\n" : "detail off\n")
    socket.flush()
  }

  function receive(line) {
    var message
    try { message = JSON.parse(line) } catch (e) { return }
    live = message
    if (message.detail) detail = message
  }

  readonly property bool onFocusedMonitor: {
    var window = root.QsWindow.window
    var focused = Hyprland.focusedMonitor
    return !!window && !!window.screen && !!focused && window.screen.name === focused.name
  }

  function viaFocused(call) {
    var items = bar && bar.moduleWidgets ? bar.moduleWidgets(moduleName) : [root]
    for (var i = 0; i < items.length; i++) if (items[i] && items[i].onFocusedMonitor) call(items[i])
  }

  IpcHandler {
    target: "omaview"
    function open(report: string): void { root.viaFocused(function(w) { w.openReport(report) }) }
    function close(): void { root.viaFocused(function(w) { w.closeReport(w.activeReport) }) }
    function edit(): void { root.viaFocused(function(w) { if (w.activeReport !== "") w.beginEdit() }) }
  }

  Timer { id: openTimer; interval: 140; onTriggered: if (root.hoveredSection !== "") root.activeReport = root.hoveredSection }
  Timer { id: closeTimer; interval: 300; onTriggered: if (!root.editing && !root.popupHovered && root.hoveredSection === "") root.activeReport = "" }

  // One collector serves every monitor's bar. Each bar starts one only while it has no
  // connection, and the lock lets one win, so losing the first bar costs about two seconds.
  Process {
    id: collector
    running: true
    command: {
      var args = [Qt.resolvedUrl("collector/omaview-collector").toString().replace("file://", ""), "--socket", root.socketPath]
      return root.mock ? args.concat(["--mock"]) : args
    }
    stderr: SplitParser { onRead: function(line) { console.warn("omaview collector:", line) } }
  }
  Timer {
    interval: 2000
    repeat: true
    running: !collector.running && !socket.connected
    onTriggered: collector.running = true
  }

  Socket {
    id: socket
    path: root.socketPath
    connected: true
    onConnectedChanged: if (connected) root.syncDetail()
    parser: SplitParser { onRead: function(line) { root.receive(line) } }
  }
  Timer {
    interval: 2000
    repeat: true
    running: !socket.connected
    onTriggered: { socket.connected = false; socket.connected = true }
  }

  implicitWidth: row.implicitWidth
  implicitHeight: row.implicitHeight

  TextMetrics { id: sectionWidth; font.family: theme.fontFamily; font.pixelSize: Style.font.body; text: "CPU 100% 100° 999W" }
  TextMetrics { id: networkWidth; font.family: theme.fontFamily; font.pixelSize: Style.font.body; text: "↑ 99.9 MB/s ↓ 99.9 MB/s" }

  Grid {
    id: row
    columns: root.vertical ? 1 : 3

    SectionButton {
      id: cpuButton
      bar: root.bar
      text: root.vertical ? F.percent(root.live.cpu ? root.live.cpu.usage : null) : F.barSection("CPU", root.live.cpu, root.fahrenheit)
      fixedWidth: root.vertical ? -1 : Math.ceil(sectionWidth.advanceWidth) + Style.space(14)
      highlighted: root.activeReport === "cpu"
      onPressed: root.openReport("cpu")
    }
    SectionButton {
      id: gpuButton
      bar: root.bar
      text: root.vertical ? F.percent(root.live.gpu && root.live.gpu[0] ? root.live.gpu[0].usage : null) : F.barSection("GPU", root.live.gpu ? root.live.gpu[0] : null, root.fahrenheit)
      fixedWidth: root.vertical ? -1 : Math.ceil(sectionWidth.advanceWidth) + Style.space(14)
      highlighted: root.activeReport === "gpu"
      onPressed: root.openReport("gpu")
    }
    SectionButton {
      id: systemButton
      bar: root.bar
      text: root.vertical ? "NET" : F.barNetwork(root.live.net)
      fixedWidth: root.vertical ? -1 : Math.ceil(networkWidth.advanceWidth) + Style.space(14)
      highlighted: root.activeReport === "system"
      onPressed: root.openReport("system")
    }
  }

  ReportPopup { id: cpuPopup; reportId: "cpu"; title: "CPU"; host: root; anchorItem: cpuButton; bar: root.bar }
  ReportPopup { id: gpuPopup; reportId: "gpu"; title: "GPU"; host: root; anchorItem: gpuButton; bar: root.bar }
  ReportPopup { id: systemPopup; reportId: "system"; title: "System"; host: root; anchorItem: systemButton; bar: root.bar }
}
