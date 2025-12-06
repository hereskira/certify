import sys
import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QLabel, QLineEdit, QMessageBox, QTextEdit, QComboBox, QGroupBox
)
from PyQt5.QtGui import QPixmap

# ------------------------
# Folders
# ------------------------
EVENTS_DIR = "events"
TEMPLATES_DIR = "templates"
os.makedirs(EVENTS_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# ------------------------
# Helper functions
# ------------------------
def load_template(template_path):
    if not os.path.exists(template_path):
        return Image.new("RGB", (1200, 900), color="white")
    return Image.open(template_path).convert("RGB")

def draw_text(image, text, position, font_size=40):
    draw = ImageDraw.Draw(image)

    font_path = "/System/Library/Fonts/Helvetica.ttc"
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

# ----------------------------------------------------------
# Certificate Generator with signature at bottom
# ----------------------------------------------------------
def generate_certificate(
    participant, event_title, template_path, output_dir,
    signatory_name, signatory_position, signature_img_path
):
    image = load_template(template_path)

    # Participant name
    draw_text(image, participant['name'], position=(1000, 680), font_size=70)

    org = participant.get('org', 'Organization')

    raw_date = participant.get("date", datetime.today().strftime("%Y-%m-%d"))
    try:
        formatted_date = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%B %d, %Y")
    except:
        formatted_date = raw_date

    draw_text(
        image,
        f"for participating in the {event_title} held by {org}",
        position=(1000, 830),
        font_size=32
    )

    draw_text(
        image,
        f"on {formatted_date}",
        position=(1000, 900),
        font_size=32
    )

    # ---------------------------------------------------
    # Signatory block at the bottom
    # ---------------------------------------------------
    img_w, img_h = image.size

    bottom_signature_y = img_h - 210
    bottom_name_y = img_h - 140
    bottom_position_y = img_h - 90

    # Signature image (optional)
    if signature_img_path and os.path.exists(signature_img_path):
        sig = Image.open(signature_img_path).convert("RGBA")

        max_width = int(img_w * 0.22)
        ratio = max_width / sig.width
        new_height = int(sig.height * ratio)
        sig = sig.resize((max_width, new_height))

        sig_x = (img_w // 2) - (sig.width // 2)
        sig_y = bottom_signature_y - (new_height // 2)

        image.paste(sig, (sig_x, sig_y), sig)

    # Signatory name
    draw_text(image, signatory_name, position=(img_w // 2, bottom_name_y), font_size=40)

    # Signatory title
    draw_text(image, signatory_position, position=(img_w // 2, bottom_position_y), font_size=32)

    # Save PDF
    safe_name = participant['name'].replace(" ", "_")
    pdf_path = os.path.join(output_dir, f"{safe_name}.pdf")
    image.save(pdf_path, "PDF", resolution=100.0)

    return pdf_path

# ------------------------
# GUI
# ------------------------
class CertifyGUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Certify Certificate Generator")
        self.setGeometry(300, 100, 550, 700)

        self.signature_path = None

        layout = QVBoxLayout()

        # ----------------------------------------------------
        # Event group
        # ----------------------------------------------------
        event_group = QGroupBox("Event Management")
        event_layout = QVBoxLayout()

        event_layout.addWidget(QLabel("Select Event"))
        self.event_combo = QComboBox()
        event_layout.addWidget(self.event_combo)

        btn_refresh = QPushButton("Refresh Events")
        btn_refresh.clicked.connect(self.refresh_event_list)
        event_layout.addWidget(btn_refresh)

        event_layout.addWidget(QLabel("Create Event"))
        self.new_event_input = QLineEdit()
        event_layout.addWidget(self.new_event_input)

        btn_create = QPushButton("Create")
        btn_create.clicked.connect(self.create_event)
        event_layout.addWidget(btn_create)

        event_group.setLayout(event_layout)
        layout.addWidget(event_group)

        # ----------------------------------------------------
        # Signatory group
        # ----------------------------------------------------
        sign_group = QGroupBox("Signatory Details")
        sign_layout = QVBoxLayout()

        sign_layout.addWidget(QLabel("Name of Signatory"))
        self.signatory_name_input = QLineEdit()
        sign_layout.addWidget(self.signatory_name_input)

        sign_layout.addWidget(QLabel("Position or Title"))
        self.signatory_position_input = QLineEdit()
        sign_layout.addWidget(self.signatory_position_input)

        # Upload signature
        self.upload_sig_btn = QPushButton("Upload Signature Image Optional")
        self.upload_sig_btn.clicked.connect(self.upload_signature)
        sign_layout.addWidget(self.upload_sig_btn)

        self.signature_preview = QLabel("(No signature uploaded)")
        self.signature_preview.setStyleSheet("color: gray;")
        sign_layout.addWidget(self.signature_preview)

        sign_group.setLayout(sign_layout)
        layout.addWidget(sign_group)

        # ----------------------------------------------------
        # Certificate processing
        # ----------------------------------------------------
        cert_group = QGroupBox("Certificate Processing")
        cert_layout = QVBoxLayout()

        btn_csv = QPushButton("Import Participants CSV")
        btn_csv.clicked.connect(self.add_participants_csv)
        cert_layout.addWidget(btn_csv)

        btn_generate = QPushButton("Generate Certificates")
        btn_generate.clicked.connect(self.generate_certificates)
        cert_layout.addWidget(btn_generate)

        cert_group.setLayout(cert_layout)
        layout.addWidget(cert_group)

        # ----------------------------------------------------
        # Log output
        # ----------------------------------------------------
        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        layout.addWidget(self.output_log)

        self.setLayout(layout)

        self.refresh_event_list()

    # ----------------------------------------------------
    # GUI functions
    # ----------------------------------------------------
    def upload_signature(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Upload Signature", "", "Image Files (*.png *.jpg *.jpeg)"
        )
        if path:
            self.signature_path = path
            preview = QPixmap(path).scaledToWidth(150)
            self.signature_preview.setPixmap(preview)
            self.output_log.append(f"Signature uploaded: {path}")

    def refresh_event_list(self):
        self.event_combo.clear()
        events = [
            d.replace("_", " ")
            for d in os.listdir(EVENTS_DIR)
            if os.path.isdir(os.path.join(EVENTS_DIR, d))
        ]
        if events:
            self.event_combo.addItems(events)
            self.output_log.append("Loaded events.")
        else:
            self.output_log.append("No events found.")

    def create_event(self):
        title = self.new_event_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Error", "Enter an event name.")
            return

        path = os.path.join(EVENTS_DIR, title.replace(" ", "_"))
        os.makedirs(path, exist_ok=True)

        self.output_log.append(f"Event created: {title}")
        self.new_event_input.clear()
        self.refresh_event_list()

    def add_participants_csv(self):
        event = self.event_combo.currentText().strip()
        if not event:
            QMessageBox.warning(self, "Error", "Select an event.")
            return

        event_path = os.path.join(EVENTS_DIR, event.replace(" ", "_"))

        file_path, _ = QFileDialog.getOpenFileName(self, "Select CSV", "", "CSV Files (*.csv)")
        if not file_path:
            return

        df = pd.read_csv(file_path)
        df.to_csv(os.path.join(event_path, "participants.csv"), index=False)

        self.output_log.append(f"Imported {len(df)} participants.")

    def generate_certificates(self):
        event = self.event_combo.currentText().strip()
        if not event:
            QMessageBox.warning(self, "Error", "Select an event.")
            return

        event_path = os.path.join(EVENTS_DIR, event.replace(" ", "_"))
        participants_csv = os.path.join(event_path, "participants.csv")

        if not os.path.exists(participants_csv):
            QMessageBox.warning(self, "Error", "No participants CSV.")
            return

        sign_name = self.signatory_name_input.text().strip()
        sign_pos = self.signatory_position_input.text().strip()

        if not sign_name or not sign_pos:
            QMessageBox.warning(self, "Error", "Enter signatory name and title.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(event_path, "certificates", timestamp)
        os.makedirs(output_dir, exist_ok=True)

        template_file, _ = QFileDialog.getOpenFileName(
            self, "Select Template", TEMPLATES_DIR, "Images (*.png *.jpg *.jpeg)"
        )
        if not template_file:
            template_file = os.path.join(TEMPLATES_DIR, "default_template.png")

        df = pd.read_csv(participants_csv)

        for _, participant in df.iterrows():
            pdf_path = generate_certificate(
                participant,
                event,
                template_file,
                output_dir,
                sign_name,
                sign_pos,
                self.signature_path
            )
            self.output_log.append(f"Generated: {pdf_path}")

# ----------------------------------------------------
# Main
# ----------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CertifyGUI()
    window.show()
    sys.exit(app.exec_())