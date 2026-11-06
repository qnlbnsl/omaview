import QtQuick
import qs.Commons
import "../lib/layout.js" as L

Item {
  id: root

  property string title
  property string reportId
  property var columns: [[]]
  property var stats: ({})
  property var theme
  property bool fahrenheit: false
  property bool editing: false
  property int addingTo: -1

  signal editRequested()
  signal doneRequested()
  signal columnsEdited(var next)

  readonly property real columnWidth: Style.space(330)
  readonly property real gap: Style.space(8)

  implicitWidth: columns.length * columnWidth + (columns.length - 1) * gap
  implicitHeight: header.height + gap + grid.implicitHeight

  onEditingChanged: addingTo = -1

  function apply(name, col, index) {
    if (name === "remove") columnsEdited(L.remove(columns, col, index))
    else if (name === "up") columnsEdited(L.moveVertical(columns, col, index, -1))
    else if (name === "down") columnsEdited(L.moveVertical(columns, col, index, 1))
    else if (name === "left") columnsEdited(L.moveAcross(columns, col, index, -1))
    else if (name === "right") columnsEdited(L.moveAcross(columns, col, index, 1))
    else if (name === "size") columnsEdited(L.cycleSize(columns, col, index))
    else if (name === "metric") columnsEdited(L.cycleMetric(columns, col, index))
  }

  Item {
    id: header
    width: parent.width
    height: Math.max(titleLabel.implicitHeight, Style.space(22))

    Label {
      id: titleLabel
      theme: root.theme
      text: root.title
      font.pixelSize: Style.font.title
      font.weight: Font.DemiBold
      anchors.verticalCenter: parent.verticalCenter
    }
    Row {
      anchors.right: parent.right
      anchors.verticalCenter: parent.verticalCenter
      spacing: Style.space(4)
      ToolButton {
        visible: root.editing
        theme: root.theme
        text: "Reset"
        onClicked: root.columnsEdited(L.defaults()[root.reportId])
      }
      ToolButton {
        theme: root.theme
        text: root.editing ? "Done" : "✎"
        onClicked: root.editing ? root.doneRequested() : root.editRequested()
      }
    }
  }

  Flickable {
    id: flick
    y: header.height + root.gap
    width: parent.width
    height: parent.height - y
    contentWidth: width
    contentHeight: grid.implicitHeight
    clip: true
    boundsBehavior: Flickable.StopAtBounds

    Row {
      id: grid
      spacing: root.gap

      Repeater {
        model: root.columns

        Column {
          id: column
          required property var modelData
          required property int index
          width: root.columnWidth
          spacing: root.gap

          Repeater {
            model: column.modelData
            CardFrame {
              required property var modelData
              required property int index
              spec: modelData
              stats: root.stats
              theme: root.theme
              fahrenheit: root.fahrenheit
              editing: root.editing
              onAction: function(name) { root.apply(name, column.index, index) }
            }
          }

          ToolButton {
            visible: root.editing
            theme: root.theme
            text: root.addingTo === column.index ? "Cancel" : "+ Add card"
            onClicked: root.addingTo = root.addingTo === column.index ? -1 : column.index
          }
          Flow {
            visible: root.editing && root.addingTo === column.index
            width: parent.width
            spacing: Style.space(4)
            Repeater {
              model: Object.keys(L.catalog)
              ToolButton {
                required property string modelData
                theme: root.theme
                text: L.catalog[modelData].label
                onClicked: { root.columnsEdited(L.add(root.columns, column.index, modelData)); root.addingTo = -1 }
              }
            }
          }
        }
      }
    }
  }
}
