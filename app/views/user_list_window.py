import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QTableWidget, 
    QTableWidgetItem, QHeaderView
)
from app.controllers.user_controller import UserController

class UserListWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Liste des Utilisateurs")
        self.setGeometry(100, 100, 800, 600)
        self.center_window()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        self.user_table = QTableWidget()
        self.layout.addWidget(self.user_table)

        self.controller = UserController()
        self.populate_user_table()

    def center_window(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def populate_user_table(self):
        users = self.controller.get_all_users()

        if not users:
            # Handle case with no users if necessary
            return

        headers = ["ID", "Username", "Prénom", "Nom", "Email", "Profil"]
        self.user_table.setColumnCount(len(headers))
        self.user_table.setHorizontalHeaderLabels(headers)
        self.user_table.setRowCount(len(users))

        for row, user_data in enumerate(users):
            self.user_table.setItem(row, 0, QTableWidgetItem(str(user_data["id"])))
            self.user_table.setItem(row, 1, QTableWidgetItem(user_data["username"]))
            self.user_table.setItem(row, 2, QTableWidgetItem(user_data["prenom"]))
            self.user_table.setItem(row, 3, QTableWidgetItem(user_data["nom"]))
            self.user_table.setItem(row, 4, QTableWidgetItem(user_data["email"]))
            self.user_table.setItem(row, 5, QTableWidgetItem(user_data["profil"]))

        # Optional: Adjust column widths
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

if __name__ == '__main__':
    # This part is for testing the window independently
    app = QApplication(sys.argv)
    # You might need to initialize the DB for testing if it's not already
    # from app.models.base import Base, engine
    # Base.metadata.create_all(bind=engine)
    window = UserListWindow()
    window.show()
    sys.exit(app.exec())
