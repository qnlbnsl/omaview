import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons as Commons

// Omarchy exposes foreground and accent but not the whole palette, and graphs need more
// than one hue, so read the current theme's colors directly.
QtObject {
  id: root

  property string fontFamily: ""
  property var palette: ({})

  readonly property color foreground: Commons.Color.popups.text
  readonly property color muted: Qt.rgba(foreground.r, foreground.g, foreground.b, 0.62)
  readonly property color card: Qt.rgba(foreground.r, foreground.g, foreground.b, 0.06)
  readonly property color track: Qt.rgba(foreground.r, foreground.g, foreground.b, 0.13)
  readonly property color grid: Qt.rgba(foreground.r, foreground.g, foreground.b, 0.09)

  readonly property var aliases: ({ red: "color1", green: "color2", yellow: "color3", orange: "color3",
                                    blue: "color4", magenta: "color5", cyan: "color6" })

  function color(name) {
    if (name === "muted") return muted
    return palette[name] || palette[aliases[name]] || foreground
  }

  function parse(text) {
    var next = {}
    var pattern = /^\s*(\w+)\s*=\s*"(#[0-9a-fA-F]{6})"/gm
    var match
    while ((match = pattern.exec(text)) !== null) next[match[1]] = match[2]
    palette = next
  }

  function reload() { file.reload() }

  property FileView file: FileView {
    id: file
    path: (Quickshell.env("HOME") || "") + "/.local/state/omarchy/current/theme/colors.toml"
    onLoaded: root.parse(text())
  }
}
