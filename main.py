import sys
from PySide6.QtWidgets import QApplication
from app.ui.views.login_view import LoginWindow
#from app.ui.views.dashboard_view import DashboardWindow
from app.ui.views.dashboard_window import DashboardWindow

class MainApplicationController:
    def __init__(self):
        self.login_window = None
        self.dashboard_window = None

    def show_login(self):
        self.login_window = LoginWindow()
        # Connect the custom signal to our transition method
        self.login_window.authenticated.connect(self.transition_to_dashboard)
        self.login_window.show()

    def transition_to_dashboard(self, authenticated_user):
        # 1. Initialize Dashboard with the User session instance payload
        self.dashboard_window = DashboardWindow(authenticated_user)
        
        # 2. Wire the logout button action to recycle state safely back to authentication screen
        self.dashboard_window.logout_btn.clicked.connect(self.transition_to_login)
        
        # 3. Present Dashboard and close down old login window tracking instance references safely
        self.dashboard_window.show()
        self.login_window.close()
        self.login_window = None

    def transition_to_login(self):
        self.dashboard_window.close()
        self.dashboard_window = None
        self.show_login()

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Run Orchestration Architecture Instantiation
    controller = MainApplicationController()
    controller.show_login()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()