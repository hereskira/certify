import sys
import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QLabel, QLineEdit, QMessageBox, QTextEdit, QComboBox, QGroupBox
)
from PyQt5.QtGui import QPixmap

# ------------------------
# Folders
# ------------------------
EVENTS_DIR = "events"
TEMPLATES_DIR = "templates"
BACKUP_DIR = "backups"

os.makedirs(EVENTS_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# ------------------------
# Helper Functions
# ------------------------
def load_template(template_path):
    if not os.path.exists(template_path):
        return Image.new("RGB", (1200, 900), color="white")
    return Image.open(template_path).convert("RGB")


def draw_text(image, text, position, font_size=40):
    draw = ImageDraw.Draw(image)
    
    # Always use local font for consistency
    font_path = os.path.join("fonts", "Roboto-VariableFont_wdth,wght.ttf")
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = position[0] - w / 2
    y = position[1] - h / 2
    draw.text((x, y), text, fill="black", font=font)


# ------------------------
# Certificate Generation
# ------------------------
def generate_certificate(participant, event_title, template_path, output_dir, signatories):
    image = load_template(template_path)
    img_w, img_h = image.size

    draw_text(image, participant['name'], position=(1000, 680), font_size=70)

    org = participant.get('org', 'Organization')
    raw_date = participant.get("date", datetime.today().strftime("%Y-%m-%d"))
    try:
        formatted_date = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%B %d, %Y")
    except:
        formatted_date = raw_date

    draw_text(image, f"for participating in the {event_title} held by {org}",
              position=(1000, 830), font_size=32)
    draw_text(image, f"on {formatted_date}", position=(1000, 900), font_size=32)

    bottom_signature_y = img_h - 210
    bottom_name_y = img_h - 140
    bottom_position_y = img_h - 90

    if signatories:
        for i, sig in enumerate(signatories):
            if len(signatories) == 1:
                x = img_w // 2
            elif len(signatories) == 2:
                x = img_w // 3 if i == 0 else 2 * img_w // 3
            else:
                x = img_w // 4 if i == 0 else img_w // 2 if i == 1 else 3 * img_w // 4

            if sig["signature_path"] and os.path.exists(sig["signature_path"]):
                s_img = Image.open(sig["signature_path"]).convert("RGBA")
                max_width = int(img_w * 0.18)
                ratio = max_width / s_img.width
                new_height = int(s_img.height * ratio)
                s_img = s_img.resize((max_width, new_height))

                sig_x = x - s_img.width // 2
                sig_y = bottom_signature_y - new_height // 2
                image.paste(s_img, (sig_x, sig_y), s_img)

            draw_text(image, sig["name"], position=(x, bottom_name_y), font_size=40)
            draw_text(image, sig["position"], position=(x, bottom_position_y), font_size=32)

    name_safe = participant['name'].replace(" ", "_")
    pdf_path = os.path.join(output_dir, f"{name_safe}.pdf")
    image.save(pdf_path, "PDF", resolution=100.0)
    return pdf_path


# ------------------------
# Modern Stylesheet
# ------------------------
MODERN_STYLE = """
QWidget {
    background-color: #F4F6FA;
    font-family: 'Segoe UI';
    font-size: 14px;
    color: #333333;
}

QGroupBox {
    background-color: #FFFFFF;
    border: 2px solid #D0D7E2;
    border-radius: 10px;
    margin-top: 12px;
    padding: 15px;
    font-size: 15px;
    font-weight: bold;
    color: #1F2937;
}

QLineEdit, QComboBox {
    background-color: #FFFFFF;
    padding: 8px;
    border-radius: 6px;
    border: 1px solid #CED3DE;
    color: #000000;
}

QPushButton {
    background-color: #2563EB;
    color: white;
    padding: 10px;
    border-radius: 8px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #1D4ED8;
}

QTextEdit {
    background: #FFFFFF;
    border-radius: 10px;
    padding: 10px;
    color: #000000;
    border: 1px solid #CED3DE;
}
"""


# ------------------------
# GUI
# ------------------------
class CertifyGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Certify: A Local Event Certificate Generator")
        self.setGeometry(300, 100, 900, 650)
        self.setStyleSheet(MODERN_STYLE)
        self.signatories = []

        main_layout = QHBoxLayout()  # Two columns

        # ---------------- LEFT COLUMN ----------------
        left_col = QVBoxLayout()

        # Event group
        event_group = QGroupBox("Event Management")
        event_layout = QVBoxLayout()
        event_layout.addWidget(QLabel("Select Event:"))
        self.event_combo = QComboBox()
        event_layout.addWidget(self.event_combo)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh_event_list)
        event_layout.addWidget(btn_refresh)

        event_layout.addWidget(QLabel("Create Event:"))
        self.new_event_input = QLineEdit()
        event_layout.addWidget(self.new_event_input)

        btn_create = QPushButton("Create")
        btn_create.clicked.connect(self.create_event)
        event_layout.addWidget(btn_create)

        event_group.setLayout(event_layout)
        left_col.addWidget(event_group)

        # Signatories group
        sign_group = QGroupBox("Signatories (Up to 3)")
        sign_layout = QVBoxLayout()
        self.signatories_layout = QVBoxLayout()
        sign_layout.addLayout(self.signatories_layout)

        btn_add_sign = QPushButton("Add Signatory")
        btn_add_sign.clicked.connect(self.add_signatory)
        sign_layout.addWidget(btn_add_sign)

        btn_remove_sign = QPushButton("Remove Last")
        btn_remove_sign.clicked.connect(self.remove_signatory)
        sign_layout.addWidget(btn_remove_sign)

        sign_group.setLayout(sign_layout)
        left_col.addWidget(sign_group)
        left_col.addStretch()

        # ---------------- RIGHT COLUMN ----------------
        right_col = QVBoxLayout()

        # Certificate actions
        cert_group = QGroupBox("Certificate Processing")
        cert_layout = QVBoxLayout()

        btn_csv = QPushButton("Import Participants CSV")
        btn_csv.clicked.connect(self.add_participants_csv)
        cert_layout.addWidget(btn_csv)

        btn_generate = QPushButton("Generate Certificates")
        btn_generate.clicked.connect(self.generate_certificates)
        cert_layout.addWidget(btn_generate)

        cert_group.setLayout(cert_layout)
        right_col.addWidget(cert_group)

        # Log output
        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        self.output_log.setMinimumHeight(350)
        right_col.addWidget(self.output_log)

        # Add columns to layout
        main_layout.addLayout(left_col, 1)
        main_layout.addLayout(right_col, 2)
        self.setLayout(main_layout)

        self.refresh_event_list()

    # ---------------- SIGNATORIES ----------------
    def add_signatory(self):
        if len(self.signatories) >= 3:
            QMessageBox.warning(self, "Limit", "Maximum of 3 signatories allowed.")
            return

        widget = QWidget()
        layout = QVBoxLayout()  # Stack vertically

        name_input = QLineEdit()
        name_input.setPlaceholderText("Name")
        layout.addWidget(name_input)

        position_input = QLineEdit()
        position_input.setPlaceholderText("Position")
        layout.addWidget(position_input)

        upload_btn = QPushButton("Upload Signature")
        layout.addWidget(upload_btn)

        preview = QLabel("(No Image)")
        preview.setFixedHeight(50)
        preview.setFixedWidth(150)
        layout.addWidget(preview)

        sig_data = {
            "widget": widget,
            "name_input": name_input,
            "position_input": position_input,
            "upload_btn": upload_btn,
            "preview": preview,
            "signature_path": None
        }

        def upload():
            path, _ = QFileDialog.getOpenFileName(
                self, "Select Signature", "", "Image Files (*.png *.jpg *.jpeg)")
            if path:
                sig_data["signature_path"] = path
                preview.setPixmap(QPixmap(path).scaledToWidth(150))

        upload_btn.clicked.connect(upload)

        widget.setLayout(layout)
        self.signatories_layout.addWidget(widget)
        self.signatories.append(sig_data)

    def remove_signatory(self):
        if not self.signatories:
            return
        sig = self.signatories.pop()
        self.signatories_layout.removeWidget(sig["widget"])
        sig["widget"].setParent(None)

    # ---------------- EVENTS ----------------
    def refresh_event_list(self):
        self.event_combo.clear()
        events = [e.replace("_", " ") for e in os.listdir(EVENTS_DIR) if os.path.isdir(os.path.join(EVENTS_DIR, e))]
        if events:
            self.event_combo.addItems(events)
            self.output_log.append("Events loaded.")
        else:
            self.output_log.append("No events found.")

    def create_event(self):
        title = self.new_event_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Error", "Enter event name.")
            return

        path = os.path.join(EVENTS_DIR, title.replace(" ", "_"))
        os.makedirs(path, exist_ok=True)

        self.new_event_input.clear()
        self.refresh_event_list()
        self.output_log.append(f"Event created: {title}")

    # ---------------- CSV ----------------
    def add_participants_csv(self):
        event = self.event_combo.currentText().strip()
        if not event:
            QMessageBox.warning(self, "Error", "Select an event.")
            return

        event_path = os.path.join(EVENTS_DIR, event.replace(" ", "_"))
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV", "", "CSV Files (*.csv)"
        )

        if not file_path:
            return

        df = pd.read_csv(file_path)
        df.to_csv(os.path.join(event_path, "participants.csv"), index=False)
        self.output_log.append(f"Imported {len(df)} participants.")

    # ---------------- CERTIFICATES ----------------
    def generate_certificates(self):
        event = self.event_combo.currentText().strip()
        if not event:
            QMessageBox.warning(self, "Error", "Select an event.")
            return

        event_path = os.path.join(EVENTS_DIR, event.replace(" ", "_"))
        participants_csv = os.path.join(event_path, "participants.csv")
        if not os.path.exists(participants_csv):
            QMessageBox.warning(self, "Error", "Participants CSV missing.")
            return

        sign_data = []
        for s in self.signatories:
            name = s["name_input"].text().strip()
            pos = s["position_input"].text().strip()
            if name and pos:
                sign_data.append({
                    "name": name,
                    "position": pos,
                    "signature_path": s["signature_path"]
                })

        if not sign_data:
            QMessageBox.warning(self, "Error", "At least one signatory required.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(event_path, "certificates", timestamp)
        os.makedirs(output_dir, exist_ok=True)

        template_file, _ = QFileDialog.getOpenFileName(
            self, "Select Template", TEMPLATES_DIR, "Images (*.png *.jpg *.jpeg)")
        if not template_file:
            template_file = os.path.join(TEMPLATES_DIR, "default_template.png")

        df = pd.read_csv(participants_csv)
        for _, participant in df.iterrows():
            pdf_path = generate_certificate(participant, event, template_file, output_dir, sign_data)
            self.output_log.append(f"Generated: {pdf_path}")

        import shutil
        backup_path = os.path.join(BACKUP_DIR, f"backup_{event.replace(' ', '_')}_{timestamp}")
        shutil.copytree(output_dir, backup_path)
        self.output_log.append(f"Backup saved: {backup_path}")


# ------------------------
# Main
# ------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CertifyGUI()
    window.show()
    sys.exit(app.exec_())