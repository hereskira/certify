import sys
from PyQt5.QtWidgets import QApplication

from certify_app.config import ensure_folders
from certify_app.gui import CertifyGUI

def main():
    ensure_folders()
    app = QApplication(sys.argv)
    window = CertifyGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
