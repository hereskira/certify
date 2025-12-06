import sys
import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QLabel, QLineEdit, QMessageBox, QTextEdit, QComboBox, QGroupBox, QScrollArea, QWidgetItem
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

# ------------------------
# Certificate Generation
# ------------------------
def generate_certificate(participant, event_title, template_path, output_dir, signatories):
    image = load_template(template_path)
    img_w, img_h = image.size

    # Participant info
    draw_text(image, participant['name'], position=(1000, 680), font_size=70)
    org = participant.get('org', 'Organization')
    raw_date = participant.get("date", datetime.today().strftime("%Y-%m-%d"))
    try:
        formatted_date = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%B %d, %Y")
    except:
        formatted_date = raw_date
    draw_text(image, f"for participating in the {event_title} held by {org}", position=(1000, 830), font_size=32)
    draw_text(image, f"on {formatted_date}", position=(1000, 900), font_size=32)

    # Signatory block at bottom
    bottom_signature_y = img_h - 210
    bottom_name_y = img_h - 140
    bottom_position_y = img_h - 90

    num_signatories = len(signatories)
    if num_signatories == 0:
        pass  # no signatories to draw
    else:
        for i, sig in enumerate(signatories):
            # Calculate horizontal positions
            if num_signatories == 1:
                x = img_w // 2
            elif num_signatories == 2:
                x = img_w // 3 if i == 0 else 2 * img_w // 3
            elif num_signatories == 3:
                x = img_w // 4 if i == 0 else img_w // 2 if i == 1 else 3 * img_w // 4

            # Signature image
            if sig['signature_path'] and os.path.exists(sig['signature_path']):
                s_img = Image.open(sig['signature_path']).convert("RGBA")
                max_width = int(img_w * 0.18)
                ratio = max_width / s_img.width
                new_height = int(s_img.height * ratio)
                s_img = s_img.resize((max_width, new_height))
                sig_x = x - s_img.width // 2
                sig_y = bottom_signature_y - new_height // 2
                image.paste(s_img, (sig_x, sig_y), s_img)

            # Name and position
            draw_text(image, sig['name'], position=(x, bottom_name_y), font_size=40)
            draw_text(image, sig['position'], position=(x, bottom_position_y), font_size=32)

    # Save PDF
    name_safe = participant['name'].replace(" ", "_")
    pdf_path = os.path.join(output_dir, f"{name_safe}.pdf")
    image.save(pdf_path, "PDF", resolution=100.0)
    return pdf_path

# ------------------------
# GUI
# ------------------------
class CertifyGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Certify Certificate Generator")
        self.setGeometry(300, 100, 600, 800)

        self.signatories = []  # list of dicts {name, position, signature_path}

        main_layout = QVBoxLayout()

        # Event group
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
        main_layout.addWidget(event_group)

        # Signatories group
        sign_group = QGroupBox("Signatories (Up to 3)")
        sign_layout = QVBoxLayout()
        self.signatories_layout = QVBoxLayout()
        sign_layout.addLayout(self.signatories_layout)

        btn_add_sign = QPushButton("Add Signatory")
        btn_add_sign.clicked.connect(self.add_signatory)
        sign_layout.addWidget(btn_add_sign)

        btn_remove_sign = QPushButton("Remove Last Signatory")
        btn_remove_sign.clicked.connect(self.remove_signatory)
        sign_layout.addWidget(btn_remove_sign)

        sign_group.setLayout(sign_layout)
        main_layout.addWidget(sign_group)

        # Certificate processing
        cert_group = QGroupBox("Certificate Processing")
        cert_layout = QVBoxLayout()
        btn_csv = QPushButton("Import Participants CSV")
        btn_csv.clicked.connect(self.add_participants_csv)
        cert_layout.addWidget(btn_csv)
        btn_generate = QPushButton("Generate Certificates")
        btn_generate.clicked.connect(self.generate_certificates)
        cert_layout.addWidget(btn_generate)
        cert_group.setLayout(cert_layout)
        main_layout.addWidget(cert_group)

        # Output log
        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        main_layout.addWidget(self.output_log)

        self.setLayout(main_layout)
        self.refresh_event_list()

    # ------------------------
    # Signatory Methods
    # ------------------------
    def add_signatory(self):
        if len(self.signatories) >= 3:
            QMessageBox.warning(self, "Limit reached", "You can only have up to 3 signatories.")
            return
        widget = QWidget()
        layout = QHBoxLayout()
        name_input = QLineEdit()
        name_input.setPlaceholderText("Name")
        position_input = QLineEdit()
        position_input.setPlaceholderText("Position/Title")
        sig_btn = QPushButton("Upload Signature")
        preview = QLabel("(No signature)")
        sig_data = {"widget": widget, "name_input": name_input, "position_input": position_input, "sig_btn": sig_btn, "preview": preview, "signature_path": None}

        def upload_sig():
            path, _ = QFileDialog.getOpenFileName(self, "Upload Signature", "", "Image Files (*.png *.jpg *.jpeg)")
            if path:
                sig_data['signature_path'] = path
                pix = QPixmap(path).scaledToWidth(100)
                preview.setPixmap(pix)
        sig_btn.clicked.connect(upload_sig)

        layout.addWidget(name_input)
        layout.addWidget(position_input)
        layout.addWidget(sig_btn)
        layout.addWidget(preview)
        widget.setLayout(layout)
        self.signatories_layout.addWidget(widget)
        self.signatories.append(sig_data)

    def remove_signatory(self):
        if self.signatories:
            sig_data = self.signatories.pop()
            widget = sig_data['widget']
            for i in reversed(range(widget.layout().count())):
                item = widget.layout().itemAt(i)
                if isinstance(item, QWidgetItem):
                    item.widget().setParent(None)
            self.signatories_layout.removeWidget(widget)
            widget.setParent(None)

    # ------------------------
    # Event Methods
    # ------------------------
    def refresh_event_list(self):
        self.event_combo.clear()
        events = [d.replace("_", " ") for d in os.listdir(EVENTS_DIR) if os.path.isdir(os.path.join(EVENTS_DIR, d))]
        if events:
            self.event_combo.addItems(events)
            self.event_combo.setCurrentIndex(0)
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

    # ------------------------
    # CSV Methods
    # ------------------------
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

    # ------------------------
    # Certificate Methods
    # ------------------------
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
        # Gather signatories
        signatory_data = []
        for sig in self.signatories:
            name = sig['name_input'].text().strip()
            pos = sig['position_input'].text().strip()
            if name and pos:
                signatory_data.append({"name": name, "position": pos, "signature_path": sig['signature_path']})
        if not signatory_data:
            QMessageBox.warning(self, "Error", "Enter at least one signatory.")
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(event_path, "certificates", timestamp)
        os.makedirs(output_dir, exist_ok=True)
        template_file, _ = QFileDialog.getOpenFileName(self, "Select Template", TEMPLATES_DIR, "Images (*.png *.jpg *.jpeg)")
        if not template_file:
            template_file = os.path.join(TEMPLATES_DIR, "default_template.png")
        df = pd.read_csv(participants_csv)
        for _, participant in df.iterrows():
            pdf_path = generate_certificate(participant, event, template_file, output_dir, signatory_data)
            self.output_log.append(f"Generated: {pdf_path}")
        # Backup
        import shutil
        backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_event_name = event.replace(" ", "_")
        backup_folder_name = f"backup_{clean_event_name}_{backup_time}"
        backup_path = os.path.join(BACKUP_DIR, backup_folder_name)
        shutil.copytree(output_dir, backup_path)
        self.output_log.append(f"Backup saved to: {backup_path}")

# ------------------------
# Main
# ------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CertifyGUI()
    window.show()
    sys.exit(app.exec_())