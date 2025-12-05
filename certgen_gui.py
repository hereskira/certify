import sys
import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QLabel, QLineEdit, QMessageBox, QTextEdit, QComboBox
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
def load_template(template_path):
    if not os.path.exists(template_path):
        return Image.new("RGB", (800, 600), color="white")
    return Image.open(template_path).convert("RGB")

def draw_text(image, text, position=(400, 300), font_size=40):
    draw = ImageDraw.Draw(image)

    # macOS font path
    font_path = "/System/Library/Fonts/Helvetica.ttc"

    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = position[0] - w / 2
    y = position[1] - h / 2

    draw.text((x, y), text, fill="black", font=font)

def generate_certificate(participant, event_title, template_path, output_dir):
    image = load_template(template_path)

    # Name (big text)
    draw_text(image, participant['name'], position=(1000, 680), font_size=70)

    # Organization
    org_name = participant.get('org', 'Organization')

    # Bottom line
    raw_date = participant.get("date", datetime.today().strftime("%Y-%m-%d"))

    try:
        parsed_date = datetime.strptime(raw_date, "%Y-%m-%d")
        formatted_date = parsed_date.strftime("%B %d, %Y")
    except:
        formatted_date = raw_date

    # First line: event + organization
    line1 = f'for participating in the {event_title} held by {org_name}'
    draw_text(image, line1, position=(1000, 830), font_size=32)

    # Second line: date only, more centered
    line2 = f'on {formatted_date}'
    draw_text(image, line2, position=(1000, 900), font_size=32)

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
        self.setWindowTitle("Certify: Local Event Certificate Generator")
        self.setGeometry(300, 100, 500, 450)
        self.layout = QVBoxLayout()
        
        # Event selection
        self.event_label = QLabel("Select Event:")
        self.event_combo = QComboBox()
        self.layout.addWidget(self.event_label)
        self.layout.addWidget(self.event_combo)
        
        # Refresh events button
        self.refresh_events_btn = QPushButton("Refresh Event List")
        self.refresh_events_btn.clicked.connect(self.refresh_event_list)
        self.layout.addWidget(self.refresh_events_btn)

        # Event creation input
        self.new_event_label = QLabel("Create New Event:")
        self.new_event_input = QLineEdit()
        self.layout.addWidget(self.new_event_label)
        self.layout.addWidget(self.new_event_input)
        self.create_event_btn = QPushButton("Create Event")
        self.create_event_btn.clicked.connect(self.create_event)
        self.layout.addWidget(self.create_event_btn)

        # Buttons
        self.add_csv_btn = QPushButton("Add Participants CSV")
        self.add_csv_btn.clicked.connect(self.add_participants_csv)
        self.layout.addWidget(self.add_csv_btn)

        self.generate_btn = QPushButton("Generate Certificates")
        self.generate_btn.clicked.connect(self.generate_certificates)
        self.layout.addWidget(self.generate_btn)

        # Output log
        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        self.layout.addWidget(self.output_log)

        self.setLayout(self.layout)

        # Initial refresh
        self.refresh_event_list()

    # ------------------------
    # GUI Methods
    # ------------------------
    def refresh_event_list(self):
        self.event_combo.clear()
        events = [f.replace('_', ' ') for f in os.listdir(EVENTS_DIR) if os.path.isdir(os.path.join(EVENTS_DIR, f))]
        if not events:
            self.output_log.append("No events found.")
            return
        self.event_combo.addItems(events)
        self.output_log.append("Event list refreshed.")

    def create_event(self):
        title = self.new_event_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Error", "Please enter a new event name.")
            return
        event_path = os.path.join(EVENTS_DIR, title.replace(" ", "_"))
        os.makedirs(event_path, exist_ok=True)
        self.output_log.append(f"Event '{title}' created at {event_path}")
        self.new_event_input.clear()
        self.refresh_event_list()

    def add_participants_csv(self):
        event = self.event_combo.currentText().strip()
        if not event:
            QMessageBox.warning(self, "Error", "Please select an event.")
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
        event = self.event_combo.currentText().strip()
        if not event:
            QMessageBox.warning(self, "Error", "Please select an event.")
            return
        event_path = os.path.join(EVENTS_DIR, event.replace(" ", "_"))
        participants_file = os.path.join(event_path, "participants.csv")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(event_path, "certificates", timestamp)
        os.makedirs(output_dir, exist_ok=True)

        if not os.path.exists(participants_file):
            QMessageBox.warning(self, "Error", f"No participants found for event '{event}'.")
            return

        template_file, _ = QFileDialog.getOpenFileName(
            self, "Select Template Image", TEMPLATES_DIR, "Images (*.png *.jpg *.jpeg)"
        )
        if not template_file:
            template_file = os.path.join(TEMPLATES_DIR, "default_template.png")

        df = pd.read_csv(participants_file)
        for _, participant in df.iterrows():
            pdf_path = generate_certificate(participant, event, template_file, output_dir)
            self.output_log.append(f"Generated certificate: {pdf_path}")


# ------------------------
# Main
# ------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CertifyGUI()
    window.show()
    sys.exit(app.exec_())