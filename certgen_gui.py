import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QFileDialog, QLabel, QLineEdit, QMessageBox

class CertGenApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Certify: Local Certificate Generator")
        self.setGeometry(100, 100, 400, 300)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Event name input
        self.event_input = QLineEdit()
        self.event_input.setPlaceholderText("Event name")
        layout.addWidget(self.event_input)

        # Select CSV button
        self.csv_button = QPushButton("Select Participant CSV")
        self.csv_button.clicked.connect(self.select_csv)
        layout.addWidget(self.csv_button)

        # Label to show selected file
        self.csv_label = QLabel("No file selected")
        layout.addWidget(self.csv_label)

        # Generate button
        self.generate_button = QPushButton("Generate Certificates")
        self.generate_button.clicked.connect(self.generate_certificates)
        layout.addWidget(self.generate_button)

        self.setLayout(layout)

        self.csv_file = None

    def select_csv(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV Files (*.csv)")
        if file_name:
            self.csv_file = file_name
            self.csv_label.setText(file_name)

    def generate_certificates(self):
        event_name = self.event_input.text().strip()
        if not event_name or not self.csv_file:
            QMessageBox.warning(self, "Error", "Please enter an event name and select a CSV file.")
            return
        
        # Here you can call your existing functions
        from certgen import create_event, add_participants_csv, generate_certificates as gen_certs
        class Args:
            pass

        # Create event
        args = Args()
        args.title = event_name
        create_event(args)

        # Add participants
        args = Args()
        args.event = event_name
        args.file = self.csv_file
        add_participants_csv(args)

        # Generate certificates
        args = Args()
        args.event = event_name
        args.template = "default_template.png"
        gen_certs(args)

        QMessageBox.information(self, "Done", f"Certificates generated for event '{event_name}'.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CertGenApp()
    window.show()
    sys.exit(app.exec_())
