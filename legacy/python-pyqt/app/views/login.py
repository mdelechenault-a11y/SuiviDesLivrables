import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, 
    QVBoxLayout, QFormLayout, QHBoxLayout,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap
import qtawesome as qta

from app.controllers.user_controller import UserController

class LoginWindow(QWidget):
    # Signal emitted on successful login, passing the user object
    login_successful = pyqtSignal(object)

    def __init__(self, user_controller: UserController):
        super().__init__()
        self.user_controller = user_controller
        self.setWindowTitle("Authentification")
        self.setFixedWidth(600)  # Increased width for the new layout

        # Main horizontal layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Left side (Icon) ---
        left_panel = QWidget()
        left_panel.setStyleSheet("background-color: #2c3e50;") # Dark blue color
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_label = QLabel()
        icon = qta.icon('fa5s.project-diagram', color='white')
        pixmap = icon.pixmap(128, 128)
        icon_label.setPixmap(pixmap)
        
        left_layout.addWidget(icon_label)

        # --- Right side (Form) ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Suivi des Livrables")
        title_font = self.font()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Nom d'utilisateur")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Mot de passe")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        form_layout.addRow(QLabel("Utilisateur:"), self.username_input)
        form_layout.addRow(QLabel("Mot de passe:"), self.password_input)

        self.login_button = QPushButton("Connexion")
        
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.login_button)
        button_layout.addStretch()

        right_layout.addWidget(title)
        right_layout.addSpacing(20)
        right_layout.addLayout(form_layout)
        right_layout.addStretch()
        right_layout.addWidget(self.error_label)
        right_layout.addLayout(button_layout)

        # Add panels to main layout
        main_layout.addWidget(left_panel, 1) # 1/3 of the space
        main_layout.addWidget(right_panel, 2) # 2/3 of the space

        # --- Connections ---
        self.login_button.clicked.connect(self.handle_login)
        self.username_input.returnPressed.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)
    
    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if not username or not password:
            self.error_label.setText("Le nom d'utilisateur et le mot de passe sont requis.")
            return

        user = self.user_controller.authenticate_user(username, password)

        if user:
            self.error_label.setText("")
            self.login_successful.emit(user)
            self.close()
        else:
            self.error_label.setText("Nom d'utilisateur ou mot de passe incorrect.")

if __name__ == '__main__':
    from qt_material import apply_stylesheet
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_blue.xml')
    
    controller = UserController()
    login_win = LoginWindow(controller)
    
    def on_login_success(user_obj):
        print(f"Login successful for user: {user_obj.username}")
        main_app_window = QWidget()
        main_app_window.setWindowTitle(f"Welcome {user_obj.prenom}")
        main_app_window.show()

    login_win.login_successful.connect(on_login_success)
    login_win.show()
    
    sys.exit(app.exec())
