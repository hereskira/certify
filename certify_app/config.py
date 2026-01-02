import os

EVENTS_DIR = "events"
TEMPLATES_DIR = "templates"
BACKUP_DIR = "backups"

ALLOWED_TEMPLATE_EXTS = (".png", ".jpg", ".jpeg")

def ensure_folders() -> None:
    os.makedirs(EVENTS_DIR, exist_ok=True)
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
