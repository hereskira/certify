import sys
import os
import json
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QLabel, QLineEdit, QMessageBox, QTextEdit, QComboBox, QGroupBox, QScrollArea
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
def load_event_metadata(event_path):
    metadata_path = os.path.join(event_path, "event.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                data = json.load(f)
            return data
        except:
            return {"organization": "", "start_date": "", "end_date": ""}
    else:
        return {"organization": "", "start_date": "", "end_date": ""}

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)

def load_template(template_path):
    if not os.path.exists(template_path):
        return Image.new("RGB", (1200, 900), color="white")
    return Image.open(template_path).convert("RGB")

def draw_text(image, text, position, font_size=40):
    draw = ImageDraw.Draw(image)
    font_path = resource_path(os.path.join("fonts", "Roboto-VariableFont_wdth,wght.ttf"))
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
def generate_certificate(participant, event_title, event_org, event_dates, template_path, output_dir, signatories):
    image = load_template(template_path)
    img_w, img_h = image.size
    draw_text(image, participant['name'], position=(1000, 680), font_size=70)
    draw_text(image, f"for participating in the {event_title} held by {event_org}", position=(1000, 830), font_size=32)
    draw_text(image, f"on {event_dates}", position=(1000, 900), font_size=32)

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
# Stylesheet
# ------------------------
MODERN_STYLE = """
QWidget { background-color: #F4F6FA; font-family: 'Segoe UI'; font-size: 14px; color: #333; }
QGroupBox { background-color: #FFFFFF; border: 2px solid #D0D7E2; border-radius: 10px; margin-top: 12px; padding: 15px; font-size: 15px; font-weight: bold; color: #1F2937; }
QLineEdit, QComboBox { background-color: #FFFFFF; padding: 8px; border-radius: 6px; border: 1px solid #CED3DE; color: #000000; }
QPushButton { background-color: #2563EB; color: white; padding: 10px; border-radius: 8px; font-weight: 600; }
QPushButton:hover { background-color: #1D4ED8; }
QTextEdit { background: #FFFFFF; border-radius: 10px; padding: 10px; color: #000000; border: 1px solid #CED3DE; }
"""

# ------------------------
# GUI
# ------------------------
class CertifyGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Certify: Certificate Generator")
        self.setGeometry(300, 100, 950, 700)
        self.setStyleSheet(MODERN_STYLE)
        self.signatories = []

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)
        content_layout = QHBoxLayout(container)

        # LEFT COLUMN
        left_col = QVBoxLayout()
        event_group = QGroupBox("Event Management")
        event_layout = QVBoxLayout()
        event_layout.addWidget(QLabel("Select Event:"))
        self.event_combo = QComboBox()
        self.event_combo.currentIndexChanged.connect(self.load_event_metadata_ui)
        event_layout.addWidget(self.event_combo)
        btn_refresh = QPushButton("Refresh Events")
        btn_refresh.clicked.connect(self.refresh_event_list)
        event_layout.addWidget(btn_refresh)
        event_layout.addWidget(QLabel("Create Event:"))
        self.new_event_input = QLineEdit()
        self.new_event_input.setPlaceholderText("Enter Event Name")
        event_layout.addWidget(self.new_event_input)
        self.event_org_input = QLineEdit()
        self.event_org_input.setPlaceholderText("Event Organization / Host")
        event_layout.addWidget(self.event_org_input)
        self.event_start_input = QLineEdit()
        self.event_start_input.setPlaceholderText("Start Date (YYYY-MM-DD)")
        event_layout.addWidget(self.event_start_input)
        self.event_end_input = QLineEdit()
        self.event_end_input.setPlaceholderText("End Date (YYYY-MM-DD)")
        event_layout.addWidget(self.event_end_input)
        btn_create = QPushButton("Create Event")
        btn_create.clicked.connect(self.create_event)
        event_layout.addWidget(btn_create)
        btn_delete = QPushButton("Delete Selected Event")
        btn_delete.clicked.connect(self.delete_event)
        event_layout.addWidget(btn_delete)
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

        # RIGHT COLUMN
        right_col = QVBoxLayout()
        cert_group = QGroupBox("Certificate Processing")
        cert_layout = QVBoxLayout()
        btn_csv = QPushButton("Import Participants CSV")
        btn_csv.clicked.connect(self.add_participants_csv)
        cert_layout.addWidget(btn_csv)
        btn_full_csv = QPushButton("Import Full Event CSV")
        btn_full_csv.clicked.connect(self.import_full_event_csv)
        cert_layout.addWidget(btn_full_csv)
        btn_template = QPushButton("Add Template")
        btn_template.clicked.connect(self.add_template)
        cert_layout.addWidget(btn_template)
        btn_generate = QPushButton("Generate Certificates")
        btn_generate.clicked.connect(self.generate_certificates)
        cert_layout.addWidget(btn_generate)
        cert_group.setLayout(cert_layout)
        right_col.addWidget(cert_group)

        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        self.output_log.setMinimumHeight(350)
        right_col.addWidget(self.output_log)

        content_layout.addLayout(left_col, 1)
        content_layout.addLayout(right_col, 2)

        self.refresh_event_list()

    def load_event_metadata_ui(self):
        event = self.event_combo.currentText().strip()
        if not event:
            self.event_org_input.clear()
            self.event_start_input.clear()
            self.event_end_input.clear()
            return
        event_path = os.path.join(EVENTS_DIR, event.replace(" ", "_"))
        metadata = load_event_metadata(event_path)
        self.event_org_input.setText(metadata.get("organization", ""))
        self.event_start_input.setText(metadata.get("start_date", ""))
        self.event_end_input.setText(metadata.get("end_date", ""))

    # Signatories
    def add_signatory(self):
        if len(self.signatories) >= 3:
            QMessageBox.warning(self, "Limit", "Maximum of 3 signatories allowed.")
            return
        widget = QWidget()
        layout = QVBoxLayout()
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
        sig_data = {"widget": widget, "name_input": name_input,
                    "position_input": position_input, "upload_btn": upload_btn,
                    "preview": preview, "signature_path": None}
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

    # Events
    def refresh_event_list(self):
        self.event_combo.blockSignals(True)
        self.event_combo.clear()
        events = [e.replace("_", " ") for e in os.listdir(EVENTS_DIR) if os.path.isdir(os.path.join(EVENTS_DIR, e))]
        if events:
            self.event_combo.addItems(events)
            self.output_log.append("Events loaded.")
            self.load_event_metadata_ui()
        else:
            self.output_log.append("No events found.")
            self.event_org_input.clear()
            self.event_start_input.clear()
            self.event_end_input.clear()
        self.event_combo.blockSignals(False)

    def create_event(self):
        title = self.new_event_input.text().strip()
        org = self.event_org_input.text().strip()
        start_date = self.event_start_input.text().strip()
        end_date = self.event_end_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Error", "Enter event name.")
            return
        # Validate dates
        if start_date:
            try: datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError: QMessageBox.warning(self, "Error", "Start date must be YYYY-MM-DD."); return
        if end_date:
            try: datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError: QMessageBox.warning(self, "Error", "End date must be YYYY-MM-DD."); return
        path = os.path.join(EVENTS_DIR, title.replace(" ", "_"))
        os.makedirs(path, exist_ok=True)
        metadata = {"title": title, "organization": org, "start_date": start_date, "end_date": end_date}
        metadata_path = os.path.join(path, "event.json")
        with open(metadata_path, "w") as f: json.dump(metadata, f)
        self.new_event_input.clear()
        self.event_org_input.clear()
        self.event_start_input.clear()
        self.event_end_input.clear()
        self.refresh_event_list()
        self.output_log.append(f"Event created: {title}")

    def delete_event(self):
        event = self.event_combo.currentText().strip()
        if not event: return
        reply = QMessageBox.question(self, "Delete Event", f"Are you sure you want to delete '{event}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            path = os.path.join(EVENTS_DIR, event.replace(" ", "_"))
            import shutil
            try:
                shutil.rmtree(path)
                self.refresh_event_list()
                self.output_log.append(f"Deleted event: {event}")
            except Exception as e:
                self.output_log.append(f"Failed to delete event: {e}")

    # CSV
    def add_participants_csv(self):
        event = self.event_combo.currentText().strip()
        if not event:
            QMessageBox.warning(self, "Error", "Select an event."); return
        event_path = os.path.join(EVENTS_DIR, event.replace(" ", "_"))
        file_path, _ = QFileDialog.getOpenFileName(self, "Select CSV", "", "CSV Files (*.csv)")
        if not file_path: return
        df = pd.read_csv(file_path)
        df.to_csv(os.path.join(event_path, "participants.csv"), index=False)
        self.output_log.append(f"Imported {len(df)} participants.")

    def import_full_event_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Full Event CSV", "", "CSV Files (*.csv)")
        if not file_path: return
        
        try:
            df = pd.read_csv(file_path)
            
            # Check for required columns
            if 'name' not in df.columns:
                QMessageBox.warning(self, "Error", "CSV must have a 'name' column for participants.")
                return
            
            # Extract event name if present
            if 'event_name' not in df.columns:
                QMessageBox.warning(self, "Error", "CSV must have an 'event_name' column.")
                return
            
            event_name = df['event_name'].iloc[0]
            if not event_name or pd.isna(event_name):
                QMessageBox.warning(self, "Error", "Event name cannot be empty.")
                return
            
            event_name = str(event_name).strip()
            event_path = os.path.join(EVENTS_DIR, event_name.replace(" ", "_"))
            
            # Check if event already exists
            if os.path.exists(event_path):
                QMessageBox.warning(self, "Error", f"Event '{event_name}' already exists. Please choose a different name or delete the existing event first.")
                return
            
            # Create new event directory
            os.makedirs(event_path, exist_ok=True)
            
            # Extract signatories if present
            signatory_cols = ['signatory_name', 'signatory_position']
            signatories_found = all(col in df.columns for col in signatory_cols)
            
            if signatories_found:
                # Get unique signatories
                sig_df = df[signatory_cols].drop_duplicates().dropna(subset=['signatory_name'])
                
                # Clear existing signatories
                while self.signatories:
                    self.remove_signatory()
                
                # Add signatories from CSV
                for _, sig_row in sig_df.iterrows():
                    if sig_row['signatory_name'].strip():
                        widget = QWidget()
                        layout = QVBoxLayout()
                        name_input = QLineEdit()
                        name_input.setText(str(sig_row['signatory_name']).strip())
                        layout.addWidget(name_input)
                        position_input = QLineEdit()
                        position_input.setText(str(sig_row['signatory_position']).strip())
                        layout.addWidget(position_input)
                        upload_btn = QPushButton("Upload Signature")
                        layout.addWidget(upload_btn)
                        preview = QLabel("(No Image)")
                        preview.setFixedHeight(50)
                        preview.setFixedWidth(150)
                        layout.addWidget(preview)
                        sig_data = {"widget": widget, "name_input": name_input,
                                    "position_input": position_input, "upload_btn": upload_btn,
                                    "preview": preview, "signature_path": None}
                        def upload(sig_data=sig_data):
                            path, _ = QFileDialog.getOpenFileName(
                                self, "Select Signature", "", "Image Files (*.png *.jpg *.jpeg)")
                            if path:
                                sig_data["signature_path"] = path
                                sig_data["preview"].setPixmap(QPixmap(path).scaledToWidth(150))
                        upload_btn.clicked.connect(upload)
                        widget.setLayout(layout)
                        self.signatories_layout.addWidget(widget)
                        self.signatories.append(sig_data)
                
                self.output_log.append(f"Imported {len(sig_df)} signatories from CSV.")
            
            # Save participants (exclude signatory and event metadata columns)
            participants_df = df[['name']].copy() if 'name' in df.columns else df
            participants_df.to_csv(os.path.join(event_path, "participants.csv"), index=False)
            self.output_log.append(f"Imported {len(participants_df)} participants.")
            
            # Import event metadata if present
            org = df['organization'].iloc[0] if 'organization' in df.columns else ""
            start_date = df['start_date'].iloc[0] if 'start_date' in df.columns else ""
            end_date = df['end_date'].iloc[0] if 'end_date' in df.columns else ""
            
            # Save event metadata
            metadata = {"title": event_name, "organization": str(org).strip() if org else "", 
                       "start_date": str(start_date).strip() if start_date else "", 
                       "end_date": str(end_date).strip() if end_date else ""}
            metadata_path = os.path.join(event_path, "event.json")
            with open(metadata_path, "w") as f: json.dump(metadata, f)
            
            # Update UI with event and metadata
            self.refresh_event_list()
            # Select the newly created event
            index = self.event_combo.findText(event_name)
            if index >= 0:
                self.event_combo.setCurrentIndex(index)
            
            self.output_log.append(f"Event '{event_name}' created successfully.")
            if org or start_date or end_date:
                self.output_log.append("Event metadata saved.")
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to import CSV: {str(e)}")

    def add_template(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Template", "", "Images (*.png *.jpg *.jpeg)")
        if not file_path: return
        dest_path = os.path.join(TEMPLATES_DIR, os.path.basename(file_path))
        import shutil
        try: shutil.copy(file_path, dest_path); self.output_log.append(f"Template added: {dest_path}")
        except Exception as e: self.output_log.append(f"Failed to add template: {e}")

    # Certificates
    def generate_certificates(self):
        event = self.event_combo.currentText().strip()
        if not event: QMessageBox.warning(self, "Error", "Select an event."); return
        event_path = os.path.join(EVENTS_DIR, event.replace(" ", "_"))
        participants_csv = os.path.join(event_path, "participants.csv")
        if not os.path.exists(participants_csv):
            QMessageBox.warning(self, "Error", "Participants CSV missing."); return

        # Read latest info from fields and save to JSON
        org = self.event_org_input.text().strip()
        start_date = self.event_start_input.text().strip()
        end_date = self.event_end_input.text().strip()
        metadata = {"title": event, "organization": org, "start_date": start_date, "end_date": end_date}
        metadata_path = os.path.join(event_path, "event.json")
        with open(metadata_path, "w") as f: json.dump(metadata, f)

        # Format date range nicely
        if start_date and end_date:
            if start_date == end_date:
                event_dates = datetime.strptime(start_date, '%Y-%m-%d').strftime('%B %-d, %Y')
            else:
                try:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    if start_dt.month == end_dt.month:
                        event_dates = f"{start_dt.strftime('%B %-d')}–{end_dt.strftime('%-d, %Y')}"
                    else:
                        event_dates = f"{start_dt.strftime('%B %-d, %Y')}–{end_dt.strftime('%B %-d, %Y')}"
                except:
                    event_dates = f"{start_date} to {end_date}"
        elif start_date:
            event_dates = start_date
        elif end_date:
            event_dates = end_date
        else:
            event_dates = ""

        sign_data = []
        for s in self.signatories:
            name = s["name_input"].text().strip()
            pos = s["position_input"].text().strip()
            if name and pos:
                sign_data.append({"name": name, "position": pos, "signature_path": s["signature_path"]})
        if not sign_data: QMessageBox.warning(self, "Error", "At least one signatory required."); return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(event_path, "certificates", timestamp)
        os.makedirs(output_dir, exist_ok=True)

        template_file, _ = QFileDialog.getOpenFileName(self, "Select Template", TEMPLATES_DIR, "Images (*.png *.jpg *.jpeg)")
        if not template_file: return

        df = pd.read_csv(participants_csv)
        for _, participant in df.iterrows():
            pdf_path = generate_certificate(participant, event, org, event_dates, template_file, output_dir, sign_data)
            self.output_log.append(f"Generated: {pdf_path}")

        # Backup only certificates
        backup_path = os.path.join(BACKUP_DIR, f"backup_{event.replace(' ', '_')}_{timestamp}")
        import shutil
        shutil.copytree(output_dir, backup_path)
        self.output_log.append(f"Backup saved: {backup_path}")

# Main
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CertifyGUI()
    window.show()
    sys.exit(app.exec_())