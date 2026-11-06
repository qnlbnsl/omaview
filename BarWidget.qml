import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import qs.Commons
import qs.Ui
import "ui"
import "lib/config.js" as C
import "lib/format.js" as F
import "lib/layout.js" as L
import "lib/pointer.js" as P

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

  // While a report is open the bar's own hover state stops following the pointer, so it's
  // read from Hyprland instead. That also double-checks the pointer before a report opens.
  property string polledSection: ""
  property bool confirmOpen: false

  // Set when a report was opened on purpose (click, command or edit), so crossing it can't close it.
  property bool passExempt: false
  property var passTracker: null
  property var config: C.parse("")
  readonly property string pointerSection: activeReport !== "" ? polledSection : hoveredSection

  // Deferred because updateHover can change activeReport, which this property depends on.
  onPointerSectionChanged: Qt.callLater(updateHover)
  onPopupHoveredChanged: updateHover()
  onSettingsChanged: localLayouts = null
  onSocketPathChanged: {
    collector.running = false
    socket.connected = false
  }

  onActiveReportChanged: {
    passTracker = null
    passExempt = false
    syncDetail()
    if (activeReport !== "") {
      lastReport = activeReport
      theme.reload()
    }
  }

  function updateHover() {
    if (editing) return
    if (pointerSection !== "") {
      closeTimer.stop()
      if (activeReport === "") {
        configFile.reload()
        openTimer.restart()
      }
      else if (!popupHovered) activeReport = pointerSection
      return
    }
    openTimer.stop()
    confirmOpen = false
    if (popupHovered) closeTimer.stop()
    else if (activeReport !== "") closeTimer.restart()
  }

  function openReport(id) {
    closeTimer.stop()
    openTimer.stop()
    saveDraft()
    confirmOpen = false
    polledSection = hoveredSection
    activeReport = id
    passExempt = true
  }

  function closeReport(id) {
    if (activeReport !== id) return
    saveDraft()
    activeReport = ""
  }

  // `omarchy-shell shell summon|hide|toggle` reach a bar widget only through these three.
  // The bar requires all of them on the root, and picks the copy on the focused monitor.
  readonly property bool opened: activeReport !== ""
  property string lastReport: "cpu"
  function open() { openReport(lastReport) }
  function close() { closeReport(activeReport) }

  function beginEdit() {
    passExempt = true
    draft = JSON.parse(JSON.stringify(layouts[activeReport]))
  }

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

  // Optional, and only ever read. Missing or invalid settings use the defaults in lib/config.js.
  // Read again each time the pointer reaches a section, because a file that doesn't exist yet
  // can't be watched.
  FileView {
    id: configFile
    path: (Quickshell.env("XDG_CONFIG_HOME") || (Quickshell.env("HOME") + "/.config")) + "/omaview/config.json"
    printErrors: false
    onLoaded: root.config = C.parse(text())
    onLoadFailed: root.config = C.parse("")
  }

  // Long enough that crossing the bar on the way to something else doesn't open a report.
  // System waits longer because it's big enough to be hard to get out of.
  Timer {
    id: openTimer
    interval: root.pointerSection === "system" ? root.config.systemOpenDelayMs : root.config.openDelayMs
    onTriggered: {
      root.confirmOpen = true
      pointerPoll.running = true
    }
  }
  Timer { id: closeTimer; interval: 300; onTriggered: if (!root.editing && !root.popupHovered && root.pointerSection === "") root.activeReport = "" }

  function sectionRect(id, button) {
    var window = root.QsWindow.window
    var origin = button.mapToItem(null, 0, 0)
    return {
      id: id,
      x: origin.x + (window && window.screen ? window.screen.x : 0),
      y: origin.y + (window && window.screen ? window.screen.y : 0),
      width: button.width,
      height: button.height
    }
  }

  function receivePointer(text) {
    var position = P.parseCursor(text)
    if (!position) return
    var section = P.sectionAt(position.x, position.y, [sectionRect("cpu", cpuButton), sectionRect("gpu", gpuButton), sectionRect("system", systemButton)])
    if (confirmOpen) {
      confirmOpen = false
      if (section !== "" && activeReport === "") {
        polledSection = section
        activeReport = section
      }
    } else if (activeReport !== "") {
      polledSection = section
      followPass(position, section)
    }
  }

  // Closes System when the pointer crosses it without stopping, so opening it by accident
  // doesn't mean travelling all the way out of it.
  function followPass(position, section) {
    if (activeReport !== "system" || passExempt || !config.closeOnPassThrough) return
    if (passTracker && passTracker.settled) return
    if (section !== "") {
      passTracker = null
    } else if (popupHovered) {
      passTracker = P.trackPass(passTracker, position.x, position.y, Date.now(), config.passThroughMs)
      if (passTracker.through) activeReport = ""
    }
  }

  Process {
    id: pointerPoll
    command: ["hyprctl", "cursorpos", "-j"]
    stdout: StdioCollector { onStreamFinished: root.receivePointer(text) }
  }
  Timer {
    interval: 80
    repeat: true
    running: root.activeReport !== "" && !root.editing
    onTriggered: pointerPoll.running = true
  }

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
