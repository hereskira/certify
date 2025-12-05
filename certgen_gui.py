import sys
import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QLabel, QLineEdit, QMessageBox, QTextEdit
)

# ------------------------
# Folders
# ------------------------
EVENTS_DIR = "events"
TEMPLATES_DIR = "templates"
os.makedirs(EVENTS_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# ------------------------
# Helper Functions
# ------------------------
def load_template(template_name):
    template_path = os.path.join(TEMPLATES_DIR, template_name)
    if not os.path.exists(template_path):
        return Image.new("RGB", (800, 600), color="white")
    return Image.open(template_path).convert("RGB")

def draw_text(image, text, position=(400, 300), font_size=40):
    draw = ImageDraw.Draw(image)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(font_path, font_size) if os.path.exists(font_path) else ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((position[0] - w/2, position[1] - h/2), text, fill="black", font=font)

def generate_certificate(participant, event_title, template_name, output_dir):
    image = load_template(template_name)
    draw_text(image, participant['name'], position=(400, 250), font_size=50)
    draw_text(image, event_title, position=(400, 350), font_size=30)
    draw_text(image, participant.get('date', datetime.today().strftime("%Y-%m-%d")), position=(400, 450), font_size=25)
    
    name_safe = participant['name'].replace(" ", "_")
    pdf_path = os.path.join(output_dir, f"{name_safe}.pdf")
    image.save(pdf_path, "PDF", resolution=100.0)
    return pdf_path

# ------------------------
# PyQt GUI
# ------------------------
class CertifyGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Certify: Local Certificate Generator")
        self.setGeometry(300, 100, 500, 400)
        self.layout = QVBoxLayout()
        
        # Event name input
        self.event_label = QLabel("Event Name:")
        self.event_input = QLineEdit()
        self.layout.addWidget(self.event_label)
        self.layout.addWidget(self.event_input)

        # Buttons
        self.create_event_btn = QPushButton("Create Event")
        self.create_event_btn.clicked.connect(self.create_event)
        self.layout.addWidget(self.create_event_btn)

        self.add_csv_btn = QPushButton("Add Participants CSV")
        self.add_csv_btn.clicked.connect(self.add_participants_csv)
        self.layout.addWidget(self.add_csv_btn)

        self.generate_btn = QPushButton("Generate Certificates")
        self.generate_btn.clicked.connect(self.generate_certificates)
        self.layout.addWidget(self.generate_btn)

        self.list_events_btn = QPushButton("List Events")
        self.list_events_btn.clicked.connect(self.list_events)
        self.layout.addWidget(self.list_events_btn)

        # Output log
        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        self.layout.addWidget(self.output_log)

        self.setLayout(self.layout)

    # ------------------------
    # GUI Methods
    # ------------------------
    def create_event(self):
        title = self.event_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Error", "Please enter an event name.")
            return
        event_path = os.path.join(EVENTS_DIR, title.replace(" ", "_"))
        os.makedirs(event_path, exist_ok=True)
        self.output_log.append(f"Event '{title}' created at {event_path}")

    def add_participants_csv(self):
        event = self.event_input.text().strip()
        if not event:
            QMessageBox.warning(self, "Error", "Please enter an event name.")
            return
        event_path = os.path.join(EVENTS_DIR, event.replace(" ", "_"))
        if not os.path.exists(event_path):
            QMessageBox.warning(self, "Error", f"Event '{event}' does not exist.")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Select Participants CSV", "", "CSV Files (*.csv)")
        if not file_path:
            return
        df = pd.read_csv(file_path)
        df.to_csv(os.path.join(event_path, "participants.csv"), index=False)
        self.output_log.append(f"Imported {len(df)} participants from {file_path}")

    def generate_certificates(self):
        event = self.event_input.text().strip()
        if not event:
            QMessageBox.warning(self, "Error", "Please enter an event name.")
            return
        event_path = os.path.join(EVENTS_DIR, event.replace(" ", "_"))
        participants_file = os.path.join(event_path, "participants.csv")
        output_dir = os.path.join(event_path, "certificates")
        os.makedirs(output_dir, exist_ok=True)

        if not os.path.exists(participants_file):
            QMessageBox.warning(self, "Error", f"No participants found for event '{event}'.")
            return

        template_file, _ = QFileDialog.getOpenFileName(self, "Select Template Image", TEMPLATES_DIR, "Images (*.png *.jpg *.jpeg)")
        if not template_file:
            template_file = "default_template.png"

        df = pd.read_csv(participants_file)
        for _, participant in df.iterrows():
            pdf_path = generate_certificate(participant, event, os.path.basename(template_file), output_dir)
            self.output_log.append(f"Generated certificate: {pdf_path}")

    def list_events(self):
        events = [f for f in os.listdir(EVENTS_DIR) if os.path.isdir(os.path.join(EVENTS_DIR, f))]
        if not events:
            self.output_log.append("No events found.")
            return
        self.output_log.append("Existing events:")
        for e in events:
            self.output_log.append(f"- {e.replace('_', ' ')}")


# ------------------------
# Main
# ------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CertifyGUI()
    window.show()
    sys.exit(app.exec_())