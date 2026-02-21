import sys
from PyQt6.QtWidgets import (
    QDialog, QLineEdit, QPushButton, QVBoxLayout, QLabel, QMessageBox
)
from app.controllers.project_controller import ProjectController

class AddClientDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajouter un Client")
        self.setModal(True)
        
        self.controller = ProjectController()
        
        self.layout = QVBoxLayout(self)
        
        self.label = QLabel("Nom du client:")
        self.name_input = QLineEdit()
        self.save_button = QPushButton("Enregistrer")
        
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.name_input)
        self.layout.addWidget(self.save_button)
        
        self.save_button.clicked.connect(self.save_client)

    def save_client(self):
        client_name = self.name_input.text()
        if not client_name:
            QMessageBox.warning(self, "Input Error", "Le nom du client ne peut pas être vide.")
            return
            
        success, message = self.controller.add_client(client_name)
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.accept()  # Close the dialog
        else:
            QMessageBox.critical(self, "Error", message)

if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dialog = AddClientDialog()
    dialog.exec()
