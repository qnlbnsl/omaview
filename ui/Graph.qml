import QtQuick
import "../lib/metrics.js" as M

Canvas {
  id: root
  property var theme
  // [{ values: [...], color: "#rrggbb" }]
  property var series: []
  property string kind: "percent"
  property bool stacked: false
  property bool mirrored: false
  property int capacity: 120

  onSeriesChanged: requestPaint()
  onWidthChanged: requestPaint()
  onHeightChanged: requestPaint()

  function xFor(i, length) { return width - (length - 1 - i) * width / (capacity - 1) }

  function area(ctx, top, bottom, color) {
    if (top.length === 0) return
    var n = top.length
    ctx.beginPath()
    ctx.moveTo(xFor(0, n), top[0])
    for (var i = 1; i < n; i++) ctx.lineTo(xFor(i, n), top[i])
    for (var j = n - 1; j >= 0; j--) ctx.lineTo(xFor(j, n), bottom[j])
    ctx.closePath()
    ctx.globalAlpha = 0.28
    ctx.fillStyle = color
    ctx.fill()
    ctx.globalAlpha = 1
    ctx.beginPath()
    ctx.moveTo(xFor(0, n), top[0])
    for (var k = 1; k < n; k++) ctx.lineTo(xFor(k, n), top[k])
    ctx.strokeStyle = color
    ctx.lineWidth = 1.4
    ctx.stroke()
  }

  onPaint: {
    var ctx = getContext("2d")
    ctx.reset()
    if (width <= 0 || height <= 0) return
    var h = height
    ctx.strokeStyle = theme ? theme.grid : "#333"
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(0, Math.round(h / 2) + 0.5)
    ctx.lineTo(width, Math.round(h / 2) + 0.5)
    ctx.stroke()

    var lists = series.map(function(s) { return s.values || [] })

    if (mirrored) {
      var mirror = M.scale(kind, lists)
      var mid = h / 2
      series.forEach(function(s, index) {
        var direction = index === 0 ? -1 : 1
        var edge = (s.values || []).map(function(v) { return mid + direction * (v / mirror.max) * (mid - 1) })
        area(ctx, edge, edge.map(function() { return mid }), s.color)
      })
      return
    }

    if (stacked) {
      var base = []
      var scale = M.scale(kind, [])
      series.forEach(function(s) {
        var values = s.values || []
        var bottom = values.map(function(_, i) { return base[i] || 0 })
        var total = values.map(function(v, i) { return bottom[i] + v })
        var yFor = function(v) { return h - Math.min(1, v / scale.max) * (h - 1) }
        area(ctx, total.map(yFor), bottom.map(yFor), s.color)
        base = total
      })
      return
    }

    var range = M.scale(kind, lists)
    series.forEach(function(s) {
      var y = (s.values || []).map(function(v) {
        return h - Math.max(0, Math.min(1, (v - range.min) / (range.max - range.min))) * (h - 1)
      })
      area(ctx, y, y.map(function() { return h }), s.color)
    })
  }
}
