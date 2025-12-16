# certify_app/gui.py
import os
import json
from datetime import datetime
from typing import List, Dict, Optional
import inspect

import pandas as pd
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QLabel, QLineEdit, QMessageBox, QTextEdit, QComboBox, QGroupBox, QScrollArea
)
from PyQt5.QtGui import QPixmap

from .config import EVENTS_DIR, TEMPLATES_DIR, BACKUP_DIR, ALLOWED_TEMPLATE_EXTS
from .helpers import sanitize_folder_name, load_event_metadata, parse_date_ymd, format_date_range
from .certificate import generate_certificate


MODERN_STYLE = """
QWidget { background-color: #F4F6FA; font-family: 'Segoe UI'; font-size: 14px; color: #333; }
QGroupBox { background-color: #FFFFFF; border: 2px solid #D0D7E2; border-radius: 10px; margin-top: 12px; padding: 15px; font-size: 15px; font-weight: bold; color: #1F2937; }
QLineEdit, QComboBox { background-color: #FFFFFF; padding: 8px; border-radius: 6px; border: 1px solid #CED3DE; color: #000000; }
QPushButton { background-color: #2563EB; color: white; padding: 10px; border-radius: 8px; font-weight: 600; }
QPushButton:hover { background-color: #1D4ED8; }
QPushButton:disabled { background-color: #93C5FD; color: #F8FAFC; }
QTextEdit { background: #FFFFFF; border-radius: 10px; padding: 10px; color: #000000; border: 1px solid #CED3DE; }
"""

IMG_FILTER = "Image Files (*.png *.jpg *.jpeg)"


class CertifyGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Certify: Certificate Generator")
        self.setGeometry(300, 100, 950, 700)
        self.setStyleSheet(MODERN_STYLE)

        self.signatories: List[Dict] = []

        # Scroll container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)
        content_layout = QHBoxLayout(container)

        # ------------------------
        # LEFT COLUMN
        # ------------------------
        left_col = QVBoxLayout()

        event_group = QGroupBox("Event Management")
        event_layout = QVBoxLayout()

        event_layout.addWidget(QLabel("Select Event:"))
        self.event_combo = QComboBox()
        self.event_combo.currentIndexChanged.connect(self._guard(self.load_event_metadata_ui))
        event_layout.addWidget(self.event_combo)

        self.btn_refresh = QPushButton("Refresh Events")
        self.btn_refresh.clicked.connect(self._guard(self.refresh_event_list))
        event_layout.addWidget(self.btn_refresh)

        event_layout.addWidget(QLabel("Create Event:"))
        self.new_event_input = QLineEdit()
        self.new_event_input.setPlaceholderText("Enter Event Name (Required)")
        self.new_event_input.textChanged.connect(lambda: self.update_button_states())
        event_layout.addWidget(self.new_event_input)

        self.event_org_input = QLineEdit()
        self.event_org_input.setPlaceholderText("Event Organization / Host")
        self.event_org_input.textChanged.connect(lambda: self.update_button_states())
        event_layout.addWidget(self.event_org_input)

        self.event_start_input = QLineEdit()
        self.event_start_input.setPlaceholderText("Start Date (YYYY-MM-DD)")
        self.event_start_input.textChanged.connect(lambda: self.update_button_states())
        event_layout.addWidget(self.event_start_input)

        self.event_end_input = QLineEdit()
        self.event_end_input.setPlaceholderText("End Date (YYYY-MM-DD)")
        self.event_end_input.textChanged.connect(lambda: self.update_button_states())
        event_layout.addWidget(self.event_end_input)

        self.btn_create = QPushButton("Create Event")
        self.btn_create.clicked.connect(self._guard(self.create_event))
        event_layout.addWidget(self.btn_create)

        self.btn_delete = QPushButton("Delete Selected Event")
        self.btn_delete.clicked.connect(self._guard(self.delete_event))
        event_layout.addWidget(self.btn_delete)

        event_group.setLayout(event_layout)
        left_col.addWidget(event_group)

        # Signatories group
        sign_group = QGroupBox("Signatories (Up to 3)")
        sign_layout = QVBoxLayout()
        self.signatories_layout = QVBoxLayout()
        sign_layout.addLayout(self.signatories_layout)

        self.btn_add_sign = QPushButton("Add Signatory")
        self.btn_add_sign.clicked.connect(self._guard(self.add_signatory))
        sign_layout.addWidget(self.btn_add_sign)

        self.btn_remove_sign = QPushButton("Remove Last")
        self.btn_remove_sign.clicked.connect(self._guard(self.remove_signatory))
        sign_layout.addWidget(self.btn_remove_sign)

        sign_group.setLayout(sign_layout)
        left_col.addWidget(sign_group)

        left_col.addStretch()

        # ------------------------
        # RIGHT COLUMN
        # ------------------------
        right_col = QVBoxLayout()

        # ✅ NEW: All-in-One option (added as an option only)
        allin_group = QGroupBox("All-in-One Option (Upload CSV → Auto Setup → Generate)")
        allin_layout = QVBoxLayout()
        allin_layout.addWidget(QLabel(
            "Upload a single CSV that includes:\n"
            "Required: event_name, name, signatory_name, signatory_position\n"
            "Optional: organization, start_date, end_date, template_file\n"
            "Then it will:\n"
            "• Create/overwrite event folder\n"
            "• Fill signatories (you upload signatures)\n"
            "• Generate all certificates"
        ))
        self.btn_all_in_one = QPushButton("All-in-one Upload CSV → Generate Certificates")
        self.btn_all_in_one.clicked.connect(self._guard(self.all_in_one_flow))
        allin_layout.addWidget(self.btn_all_in_one)
        allin_group.setLayout(allin_layout)
        right_col.addWidget(allin_group)

        cert_group = QGroupBox("Certificate Processing (Classic Workflow)")
        cert_layout = QVBoxLayout()

        self.btn_csv = QPushButton("Import Participants CSV")
        self.btn_csv.clicked.connect(self._guard(self.add_participants_csv))
        cert_layout.addWidget(self.btn_csv)

        self.btn_template = QPushButton("Add Template")
        self.btn_template.clicked.connect(self._guard(self.add_template))
        cert_layout.addWidget(self.btn_template)

        self.btn_generate = QPushButton("Generate Certificates")
        self.btn_generate.clicked.connect(self._guard(self.generate_certificates))
        cert_layout.addWidget(self.btn_generate)

        cert_group.setLayout(cert_layout)
        right_col.addWidget(cert_group)

        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        self.output_log.setMinimumHeight(350)
        right_col.addWidget(self.output_log)

        content_layout.addLayout(left_col, 1)
        content_layout.addLayout(right_col, 2)

        self.refresh_event_list()
        self.update_button_states()

    # ------------------------
    # Guard wrapper: prevents crash + ignores extra signal args safely
    # ------------------------
    def _guard(self, fn):
        sig = inspect.signature(fn)
        params = [
            p for p in sig.parameters.values()
            if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        has_varargs = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())

        def wrapped(*args, **kwargs):
            try:
                if has_varargs:
                    return fn(*args, **kwargs)
                clipped = args[:len(params)]
                return fn(*clipped, **kwargs)
            except Exception as e:
                self.log(f"[ERROR] {type(e).__name__}: {e}")
                QMessageBox.critical(self, "Unexpected Error", f"{type(e).__name__}: {e}")
                self.update_button_states()
        return wrapped

    def log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.output_log.append(f"[{ts}] {msg}")

    # ------------------------
    # State helpers
    # ------------------------
    def selected_event(self) -> str:
        return (self.event_combo.currentText() or "").strip()

    def event_path_for(self, event_name: str) -> str:
        return os.path.join(EVENTS_DIR, sanitize_folder_name(event_name))

    def participants_csv_path(self) -> str:
        ev = self.selected_event()
        return os.path.join(self.event_path_for(ev), "participants.csv") if ev else ""

    def templates_available(self) -> bool:
        try:
            return any(f.lower().endswith(ALLOWED_TEMPLATE_EXTS) for f in os.listdir(TEMPLATES_DIR))
        except Exception:
            return False

    def valid_signatories(self) -> List[Dict]:
        out = []
        for s in self.signatories:
            name = s["name_input"].text().strip()
            pos = s["position_input"].text().strip()
            if name and pos:
                out.append({"name": name, "position": pos, "signature_path": s.get("signature_path")})
        return out

    def update_button_states(self) -> None:
        event_selected = bool(self.selected_event())
        participants_ok = event_selected and os.path.exists(self.participants_csv_path())
        sign_ok = len(self.valid_signatories()) >= 1
        template_ok = self.templates_available()

        # Create event requires a name
        can_create = bool(self.new_event_input.text().strip())
        self.btn_create.setEnabled(can_create)

        # Delete/import require an event selected
        self.btn_delete.setEnabled(event_selected)
        self.btn_csv.setEnabled(event_selected)

        # Generate requires: event + participants + signatory + template
        self.btn_generate.setEnabled(event_selected and participants_ok and sign_ok and template_ok)

        # Remove signatory only if exists
        self.btn_remove_sign.setEnabled(len(self.signatories) > 0)

        self.btn_generate.setToolTip(
            "To enable Generate:\n"
            "1) Select an event\n"
            "2) Import participants CSV (must include 'name' column)\n"
            "3) Add at least 1 signatory (name + position)\n"
            "4) Add at least 1 template in /templates\n"
        )

    # ========================
    # ✅ All-in-One Option
    # ========================
    def _resolve_template_path(self, template_hint: str) -> Optional[str]:
        hint = (template_hint or "").strip()
        if not hint:
            return None

        # absolute path
        if os.path.isabs(hint) and os.path.exists(hint):
            return hint

        # filename inside templates/
        candidate = os.path.join(TEMPLATES_DIR, hint)
        if os.path.exists(candidate):
            return candidate

        return None

    def _parse_all_in_one_csv(self, csv_path: str) -> dict:
        df = pd.read_csv(csv_path)

        # required columns
        for col in ["event_name", "name", "signatory_name", "signatory_position"]:
            if col not in df.columns:
                raise ValueError(f"CSV missing required column: {col}")

        # event_name
        ev_series = df["event_name"].dropna().astype(str).map(str.strip)
        ev_series = ev_series[ev_series != ""]
        if ev_series.empty:
            raise ValueError("event_name cannot be empty.")
        event_name = ev_series.iloc[0]

        # participants
        names = df["name"].dropna().astype(str).map(str.strip)
        names = names[names != ""]
        if names.empty:
            raise ValueError("No valid participants. Column 'name' is empty.")
        participants = list(dict.fromkeys(names.tolist()))  # unique, keep order

        # optional metadata
        def pick_first(col: str) -> str:
            if col not in df.columns:
                return ""
            s = df[col].dropna().astype(str).map(str.strip)
            s = s[s != ""]
            return s.iloc[0] if not s.empty else ""

        organization = pick_first("organization")
        start_date = pick_first("start_date")
        end_date = pick_first("end_date")
        template_file = pick_first("template_file")

        if start_date:
            parse_date_ymd(start_date)
        if end_date:
            parse_date_ymd(end_date)

        # signatories: unique pairs, max 3
        sig_df = df[["signatory_name", "signatory_position"]].dropna()
        sig_df["signatory_name"] = sig_df["signatory_name"].astype(str).map(str.strip)
        sig_df["signatory_position"] = sig_df["signatory_position"].astype(str).map(str.strip)
        sig_df = sig_df[(sig_df["signatory_name"] != "") & (sig_df["signatory_position"] != "")]
        sig_df = sig_df.drop_duplicates()

        signatories = []
        for _, row in sig_df.iterrows():
            signatories.append({
                "name": row["signatory_name"],
                "position": row["signatory_position"],
                "signature_path": None
            })
            if len(signatories) >= 3:
                break

        if not signatories:
            raise ValueError("No valid signatories found in CSV.")

        return {
            "event_name": event_name,
            "organization": organization,
            "start_date": start_date,
            "end_date": end_date,
            "participants": participants,
            "signatories": signatories,
            "template_file": template_file,
        }

    def clear_signatories_ui(self) -> None:
        while self.signatories:
            sig = self.signatories.pop()
            self.signatories_layout.removeWidget(sig["widget"])
            sig["widget"].setParent(None)
        self.update_button_states()

    def all_in_one_flow(self, *_):
        os.makedirs(EVENTS_DIR, exist_ok=True)
        os.makedirs(TEMPLATES_DIR, exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)

        csv_path, _ = QFileDialog.getOpenFileName(self, "Select All-in-One CSV", "", "CSV Files (*.csv)")
        if not csv_path:
            return

        self.log(f"All-in-One CSV selected: {csv_path}")

        try:
            payload = self._parse_all_in_one_csv(csv_path)
        except Exception as e:
            QMessageBox.warning(self, "Invalid CSV", str(e))
            self.log(f"[FAILED] CSV parse: {e}")
            return

        event_name = payload["event_name"]
        org = payload["organization"]
        start_date = payload["start_date"]
        end_date = payload["end_date"]
        participants = payload["participants"]
        signatories = payload["signatories"]
        template_hint = payload["template_file"]

        folder = sanitize_folder_name(event_name)
        if not folder:
            QMessageBox.warning(self, "Invalid", "Invalid event_name for folder creation.")
            return

        event_path = os.path.join(EVENTS_DIR, folder)

        # If folder exists, ask: overwrite or create new
        if os.path.exists(event_path):
            reply = QMessageBox.question(
                self, "Event Exists",
                f"Event folder already exists:\n{event_path}\n\n"
                "YES = Overwrite participants/event.json in the same folder\n"
                "NO = Create a new folder with timestamp",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                folder = f"{folder}_{ts}"
                event_path = os.path.join(EVENTS_DIR, folder)

        os.makedirs(event_path, exist_ok=True)
        self.log(f"Using event folder: {event_path}")

        # Save event.json and participants.csv
        try:
            with open(os.path.join(event_path, "event.json"), "w", encoding="utf-8") as f:
                json.dump(
                    {"title": event_name, "organization": org, "start_date": start_date, "end_date": end_date},
                    f, ensure_ascii=False, indent=2
                )
            pd.DataFrame({"name": participants}).to_csv(os.path.join(event_path, "participants.csv"), index=False)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save event files: {e}")
            self.log(f"[FAILED] save files: {e}")
            return

        # Update UI: refresh events + select this folder
        self.refresh_event_list()
        display_name = folder.replace("_", " ")
        idx = self.event_combo.findText(display_name)
        if idx >= 0:
            self.event_combo.setCurrentIndex(idx)

        # Fill the left-side input fields
        self.event_org_input.setText(org)
        self.event_start_input.setText(start_date)
        self.event_end_input.setText(end_date)

        # Clear and populate signatories UI based on CSV
        self.clear_signatories_ui()
        self.log("Filling signatories from CSV...")

        for sig in signatories:
            # create signatory widget like classic flow
            widget = QWidget()
            layout = QVBoxLayout()

            name_input = QLineEdit()
            name_input.setPlaceholderText("Name")
            name_input.setText(sig["name"])
            name_input.textChanged.connect(lambda: self.update_button_states())
            layout.addWidget(name_input)

            position_input = QLineEdit()
            position_input.setPlaceholderText("Position")
            position_input.setText(sig["position"])
            position_input.textChanged.connect(lambda: self.update_button_states())
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
                "signature_path": None,
            }

            def upload_signature_for(sig_data=sig_data):
                path, _ = QFileDialog.getOpenFileName(self, "Select Signature", "", IMG_FILTER)
                if not path:
                    return
                sig_data["signature_path"] = path
                try:
                    sig_data["preview"].setPixmap(QPixmap(path).scaledToWidth(150))
                except Exception:
                    sig_data["preview"].setText("(Preview failed)")
                self.update_button_states()

            upload_btn.clicked.connect(self._guard(upload_signature_for))

            widget.setLayout(layout)
            self.signatories_layout.addWidget(widget)
            self.signatories.append(sig_data)

        self.update_button_states()

        # Ask user to upload signatures now (optional but recommended)
        for s in self.signatories:
            who = s["name_input"].text().strip()
            pos = s["position_input"].text().strip()
            QMessageBox.information(self, "Signature Upload", f"Upload signature for:\n{who} — {pos}")
            path, _ = QFileDialog.getOpenFileName(self, "Select Signature", "", IMG_FILTER)
            if not path:
                cancel = QMessageBox.question(
                    self, "No signature selected",
                    f"No signature selected for {who}.\nContinue without signature image?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if cancel == QMessageBox.No:
                    self.log("All-in-One canceled during signature upload.")
                    return
                continue
            s["signature_path"] = path
            try:
                s["preview"].setPixmap(QPixmap(path).scaledToWidth(150))
            except Exception:
                s["preview"].setText("(Preview failed)")

        # Template: use CSV hint if valid, else prompt
        template_path = self._resolve_template_path(template_hint)
        if not template_path:
            template_path, _ = QFileDialog.getOpenFileName(
                self, "Select Template", TEMPLATES_DIR, IMG_FILTER
            )
            if not template_path:
                QMessageBox.warning(self, "Missing Template", "No template selected. Canceled.")
                return

        # Generate certificates automatically
        sign_data = self.valid_signatories()
        if not sign_data:
            QMessageBox.warning(self, "Missing Signatory", "Need at least 1 signatory (name + position).")
            return

        participants_csv = os.path.join(event_path, "participants.csv")
        if not os.path.exists(participants_csv):
            QMessageBox.warning(self, "Missing CSV", "participants.csv missing in event folder.")
            return

        # Format event date range
        event_dates = format_date_range(start_date, end_date)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(event_path, "certificates", ts)
        os.makedirs(output_dir, exist_ok=True)

        try:
            df = pd.read_csv(participants_csv)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to read participants.csv: {e}")
            return

        if "name" not in df.columns:
            QMessageBox.warning(self, "Invalid CSV", "participants.csv must contain 'name' column.")
            return

        generated = 0
        failed = 0

        self.log(f"Generating certificates → {output_dir}")
        for _, row in df.iterrows():
            pname = str(row.get("name", "")).strip()
            if not pname:
                failed += 1
                continue
            try:
                pdf_path = generate_certificate(
                    participant_name=pname,
                    event_title=event_name,
                    event_org=org,
                    event_dates=event_dates,
                    template_path=template_path,
                    output_dir=output_dir,
                    signatories=sign_data,
                )
                self.log(f"Generated: {pdf_path}")
                generated += 1
            except Exception as e:
                failed += 1
                self.log(f"[FAILED] {pname}: {e}")

        # Backup output
        import shutil
        backup_path = os.path.join(BACKUP_DIR, f"backup_{sanitize_folder_name(folder)}_{ts}")
        try:
            shutil.copytree(output_dir, backup_path)
            self.log(f"Backup saved: {backup_path}")
        except Exception as e:
            self.log(f"[WARN] Backup failed: {e}")

        QMessageBox.information(
            self, "All-in-One Done",
            f"Finished!\nGenerated: {generated}\nFailed/Skipped: {failed}\nOutput:\n{output_dir}"
        )
        self.update_button_states()

    # ========================
    # Classic workflow (existing)
    # ========================

    # ------------------------
    # Events
    # ------------------------
    def refresh_event_list(self, *_):
        os.makedirs(EVENTS_DIR, exist_ok=True)

        self.event_combo.blockSignals(True)
        self.event_combo.clear()

        events = []
        try:
            for folder in os.listdir(EVENTS_DIR):
                full = os.path.join(EVENTS_DIR, folder)
                if os.path.isdir(full):
                    events.append(folder.replace("_", " "))
            events.sort()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to read events folder: {e}")

        if events:
            self.event_combo.addItems(events)
            self.log("Events loaded.")
            self.load_event_metadata_ui()
        else:
            self.log("No events found.")
            self.event_org_input.clear()
            self.event_start_input.clear()
            self.event_end_input.clear()

        self.event_combo.blockSignals(False)
        self.update_button_states()

    def load_event_metadata_ui(self, *_):
        ev = self.selected_event()
        if not ev:
            self.event_org_input.clear()
            self.event_start_input.clear()
            self.event_end_input.clear()
            self.update_button_states()
            return

        path = self.event_path_for(ev)
        meta = load_event_metadata(path)
        self.event_org_input.setText(meta.get("organization", ""))
        self.event_start_input.setText(meta.get("start_date", ""))
        self.event_end_input.setText(meta.get("end_date", ""))

        self.update_button_states()

    def create_event(self, *_):
        title = self.new_event_input.text().strip()
        org = self.event_org_input.text().strip()
        start_date = self.event_start_input.text().strip()
        end_date = self.event_end_input.text().strip()

        if not title:
            QMessageBox.warning(self, "Missing info", "Please enter an event name before creating.")
            return

        if start_date:
            try:
                parse_date_ymd(start_date)
            except ValueError:
                QMessageBox.warning(self, "Invalid date", "Start date must be YYYY-MM-DD.")
                return

        if end_date:
            try:
                parse_date_ymd(end_date)
            except ValueError:
                QMessageBox.warning(self, "Invalid date", "End date must be YYYY-MM-DD.")
                return

        folder = sanitize_folder_name(title)
        if not folder:
            QMessageBox.warning(self, "Invalid name", "Event name contains invalid characters.")
            return

        path = os.path.join(EVENTS_DIR, folder)
        if os.path.exists(path):
            QMessageBox.warning(self, "Already exists", f"Event '{title}' already exists.")
            return

        os.makedirs(path, exist_ok=True)

        metadata = {
            "title": title,
            "organization": org,
            "start_date": start_date,
            "end_date": end_date,
        }

        try:
            with open(os.path.join(path, "event.json"), "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save event.json: {e}")
            return

        self.new_event_input.clear()
        self.refresh_event_list()

        idx = self.event_combo.findText(title)
        if idx >= 0:
            self.event_combo.setCurrentIndex(idx)

        self.log(f"Event created: {title}")
        self.update_button_states()

    def delete_event(self, *_):
        ev = self.selected_event()
        if not ev:
            QMessageBox.warning(self, "Error", "Select an event first.")
            return

        reply = QMessageBox.question(
            self, "Delete Event", f"Are you sure you want to delete '{ev}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        import shutil
        try:
            shutil.rmtree(self.event_path_for(ev))
            self.log(f"Deleted event: {ev}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to delete event: {e}")
            self.log(f"[FAILED] delete_event: {e}")

        self.refresh_event_list()
        self.update_button_states()

    # ------------------------
    # Signatories
    # ------------------------
    def add_signatory(self, *_):
        if len(self.signatories) >= 3:
            QMessageBox.warning(self, "Limit", "Maximum of 3 signatories allowed.")
            return

        widget = QWidget()
        layout = QVBoxLayout()

        name_input = QLineEdit()
        name_input.setPlaceholderText("Name")
        name_input.textChanged.connect(lambda: self.update_button_states())
        layout.addWidget(name_input)

        position_input = QLineEdit()
        position_input.setPlaceholderText("Position")
        position_input.textChanged.connect(lambda: self.update_button_states())
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
            "signature_path": None,
        }

        def upload_signature(*_):
            path, _ = QFileDialog.getOpenFileName(self, "Select Signature", "", IMG_FILTER)
            if not path:
                return
            sig_data["signature_path"] = path
            try:
                preview.setPixmap(QPixmap(path).scaledToWidth(150))
            except Exception:
                preview.setText("(Preview failed)")
            self.update_button_states()

        upload_btn.clicked.connect(self._guard(upload_signature))

        widget.setLayout(layout)
        self.signatories_layout.addWidget(widget)
        self.signatories.append(sig_data)

        self.log("Signatory added.")
        self.update_button_states()

    def remove_signatory(self, *_):
        if not self.signatories:
            QMessageBox.information(self, "Info", "No signatories to remove.")
            return

        sig = self.signatories.pop()
        self.signatories_layout.removeWidget(sig["widget"])
        sig["widget"].setParent(None)

        self.log("Removed last signatory.")
        self.update_button_states()

    # ------------------------
    # Templates
    # ------------------------
    def add_template(self, *_):
        os.makedirs(TEMPLATES_DIR, exist_ok=True)

        file_path, _ = QFileDialog.getOpenFileName(self, "Select Template", "", IMG_FILTER)
        if not file_path:
            return

        if not file_path.lower().endswith(ALLOWED_TEMPLATE_EXTS):
            QMessageBox.warning(self, "Invalid file", "Template must be a PNG/JPG/JPEG.")
            return

        dest_path = os.path.join(TEMPLATES_DIR, os.path.basename(file_path))

        import shutil
        try:
            shutil.copy(file_path, dest_path)
            self.log(f"Template added: {dest_path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to add template: {e}")
            self.log(f"[FAILED] add_template: {e}")

        self.update_button_states()

    # ------------------------
    # CSV (classic)
    # ------------------------
    def add_participants_csv(self, *_):
        ev = self.selected_event()
        if not ev:
            QMessageBox.warning(self, "Missing info", "Select an event first.")
            return

        event_path = self.event_path_for(ev)
        os.makedirs(event_path, exist_ok=True)

        file_path, _ = QFileDialog.getOpenFileName(self, "Select CSV", "", "CSV Files (*.csv)")
        if not file_path:
            return

        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to read CSV: {e}")
            return

        if "name" not in df.columns:
            QMessageBox.warning(self, "Invalid CSV", "CSV must contain a 'name' column.")
            return

        try:
            df.to_csv(os.path.join(event_path, "participants.csv"), index=False)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save participants.csv: {e}")
            return

        self.log(f"Imported {len(df)} participants for '{ev}'.")
        self.update_button_states()

    # ------------------------
    # Generate Certificates (classic)
    # ------------------------
    def generate_certificates(self, *_):
        ev = self.selected_event()
        if not ev:
            QMessageBox.warning(self, "Missing info", "Select an event first.")
            return

        event_path = self.event_path_for(ev)
        participants_csv = os.path.join(event_path, "participants.csv")
        if not os.path.exists(participants_csv):
            QMessageBox.warning(self, "Missing file", "Participants CSV missing. Import participants first.")
            return

        sign_data = self.valid_signatories()
        if not sign_data:
            QMessageBox.warning(self, "Missing info", "Add at least 1 signatory (name + position).")
            return

        if not self.templates_available():
            QMessageBox.warning(self, "Missing templates", "No templates found. Click 'Add Template' first.")
            return

        org = self.event_org_input.text().strip()
        start_date = self.event_start_input.text().strip()
        end_date = self.event_end_input.text().strip()

        if start_date:
            try:
                parse_date_ymd(start_date)
            except ValueError:
                QMessageBox.warning(self, "Invalid date", "Start date must be YYYY-MM-DD.")
                return

        if end_date:
            try:
                parse_date_ymd(end_date)
            except ValueError:
                QMessageBox.warning(self, "Invalid date", "End date must be YYYY-MM-DD.")
                return

        try:
            with open(os.path.join(event_path, "event.json"), "w", encoding="utf-8") as f:
                json.dump(
                    {"title": ev, "organization": org, "start_date": start_date, "end_date": end_date},
                    f, ensure_ascii=False, indent=2
                )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save event.json: {e}")
            return

        event_dates = format_date_range(start_date, end_date)

        template_file, _ = QFileDialog.getOpenFileName(
            self, "Select Template", TEMPLATES_DIR, IMG_FILTER
        )
        if not template_file:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(event_path, "certificates", timestamp)
        os.makedirs(output_dir, exist_ok=True)

        try:
            df = pd.read_csv(participants_csv)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to read participants.csv: {e}")
            return

        if "name" not in df.columns:
            QMessageBox.warning(self, "Invalid CSV", "participants.csv must have a 'name' column.")
            return

        generated = 0
        failed = 0

        for _, row in df.iterrows():
            name = str(row.get("name", "")).strip()
            if not name:
                failed += 1
                self.log("Skipped empty name.")
                continue

            try:
                pdf_path = generate_certificate(
                    participant_name=name,
                    event_title=ev,
                    event_org=org,
                    event_dates=event_dates,
                    template_path=template_file,
                    output_dir=output_dir,
                    signatories=sign_data,
                )
                self.log(f"Generated: {pdf_path}")
                generated += 1
            except Exception as e:
                failed += 1
                self.log(f"[FAILED] {name}: {e}")

        import shutil
        backup_path = os.path.join(BACKUP_DIR, f"backup_{sanitize_folder_name(ev)}_{timestamp}")
        try:
            shutil.copytree(output_dir, backup_path)
            self.log(f"Backup saved: {backup_path}")
        except Exception as e:
            self.log(f"[WARN] Backup failed: {e}")

        QMessageBox.information(
            self, "Done",
            f"Finished!\nGenerated: {generated}\nFailed/Skipped: {failed}\nOutput: {output_dir}"
        )
        self.update_button_states()
