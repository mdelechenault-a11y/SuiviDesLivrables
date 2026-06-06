from PyQt6.QtWidgets import QWidget, QVBoxLayout, QToolButton, QSizePolicy, QFrame, QTreeView
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QStandardItemModel, QStandardItem
import qtawesome as qta

class SidebarWidget(QWidget):
    """
    A retractable sidebar navigation widget.
    """
    item_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(200)
        self.is_expanded = True

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)

        self.toggle_button = QToolButton()
        self.toggle_button.setIcon(qta.icon('fa5s.bars', color='white'))
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True)
        self.toggle_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.toggle_button.clicked.connect(self.toggle_sidebar)
        self.main_layout.addWidget(self.toggle_button)

        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_model = QStandardItemModel()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.expandAll()
        self.tree_view.clicked.connect(self.on_item_clicked)
        self.tree_view.setStyleSheet("""
            QTreeView {
                background-color: #2c3e50;
                color: white;
                border: none;
            }
            QTreeView::item {
                padding: 10px;
            }
            QTreeView::item:hover {
                background-color: #34495e;
            }
            QTreeView::item:selected {
                background-color: #34495e;
            }
        """)
        self.tree_view.setIndentation(20)
        self.tree_view.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.main_layout.addWidget(self.tree_view)
        self.main_layout.addStretch()
    def add_item(self, icon_name, text, item_id, parent_item=None):
        item = QStandardItem(qta.icon(icon_name, color='white'), text)
        item.setData(item_id, Qt.ItemDataRole.UserRole)
        item.setData(text, Qt.ItemDataRole.ToolTipRole)
        if parent_item:
            parent_item.appendRow(item)
        else:
            self.tree_model.appendRow(item)
        return item

    def on_item_clicked(self, index):
        item = self.tree_model.itemFromIndex(index)
        item_id = item.data(Qt.ItemDataRole.UserRole)
        if item_id:
            self.item_selected.emit(item_id)

    def toggle_sidebar(self):
        self.is_expanded = not self.is_expanded
        self.toggle_button.setChecked(self.is_expanded)

        if self.is_expanded:
            self.setFixedWidth(200)
            self.toggle_button.setVisible(True)
            self.tree_view.setVisible(True)
        else:
            self.setFixedWidth(50)
            self.toggle_button.setVisible(False)
            self.tree_view.setVisible(False)
