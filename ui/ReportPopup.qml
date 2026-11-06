import QtQuick
import qs.Commons
import qs.Ui

PopupCard {
  id: root
  property string reportId
  property string title
  property var host

  owner: QtObject { function close() { root.host.closeReport(root.reportId) } }
  open: host.activeReport === reportId
  triggerMode: host.editing && open ? "click" : "hover"

  readonly property real inset: verticalContentInset
  contentWidth: fittedContentWidth((loader.item ? loader.item.implicitWidth : Style.space(320)) + inset)
  contentHeight: fittedContentHeight(loader.item ? loader.item.implicitHeight : Style.space(200))

  onContentWidthChanged: anchor.updateAnchor()
  onContentHeightChanged: anchor.updateAnchor()

  Loader {
    id: loader
    anchors.fill: parent
    active: root.open || root.visible
    sourceComponent: Report {
      title: root.title
      reportId: root.reportId
      columns: root.host.draft && root.open ? root.host.draft : root.host.layouts[root.reportId]
      stats: root.host.detail
      theme: root.host.theme
      fahrenheit: root.host.fahrenheit
      editing: root.host.editing
      onEditRequested: root.host.beginEdit()
      onDoneRequested: root.host.saveDraft()
      onColumnsEdited: function(next) { root.host.draft = next }
    }
  }
}
