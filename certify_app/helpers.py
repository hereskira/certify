import os
import sys
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any

def sanitize_folder_name(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"[<>:\"/\\|?*\x00-\x1F]", "", name)
    name = re.sub(r"\s+", "_", name)
    return name[:80] if name else ""

def safe_filename(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"[<>:\"/\\|?*\x00-\x1F]", "", name)
    name = re.sub(r"\s+", "_", name)
    return name[:120] if name else "participant"

def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    # if running normally, __file__ is inside certify_app/, so go up one level
    base_path = os.path.abspath(os.path.join(base_path, ".."))
    return os.path.join(base_path, relative_path)

def load_event_metadata(event_path: str) -> Dict[str, Any]:
    metadata_path = os.path.join(event_path, "event.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {"organization": "", "start_date": "", "end_date": ""}

def parse_date_ymd(s: str) -> Optional[datetime]:
    s = (s or "").strip()
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d")

def format_date_range(start_date: str, end_date: str) -> str:
    start_date = (start_date or "").strip()
    end_date = (end_date or "").strip()

    if not start_date and not end_date:
        return ""

    def fmt(dt: datetime, with_year: bool = True) -> str:
        if with_year:
            return f"{dt.strftime('%B')} {dt.day}, {dt.year}"
        return f"{dt.strftime('%B')} {dt.day}"

    try:
        sdt = parse_date_ymd(start_date) if start_date else None
        edt = parse_date_ymd(end_date) if end_date else None
    except ValueError:
        if start_date and end_date:
            return f"{start_date} to {end_date}"
        return start_date or end_date

    if sdt and edt:
        if sdt.date() == edt.date():
            return fmt(sdt, True)
        if sdt.year == edt.year and sdt.month == edt.month:
            return f"{sdt.strftime('%B')} {sdt.day}–{edt.day}, {sdt.year}"
        return f"{fmt(sdt, True)}–{fmt(edt, True)}"
    if sdt:
        return fmt(sdt, True)
    return fmt(edt, True) if edt else ""
