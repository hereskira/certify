import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import argparse
from datetime import datetime

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
        print(f"Template '{template_name}' not found. Using blank template.")
        return Image.new("RGB", (800, 600), color="white")
    return Image.open(template_path).convert("RGB")

def draw_text(image, text, position=(400, 300), font_size=40):
    draw = ImageDraw.Draw(image)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(font_path, font_size) if os.path.exists(font_path) else ImageFont.load_default()
    
    # Get text size using textbbox (works in Pillow >= 10)
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    draw.text((position[0] - w/2, position[1] - h/2), text, fill="black", font=font)

def generate_certificate(participant, event_title, template_name, output_dir):
    image = load_template(template_name)
    
    # Draw dynamic fields
    draw_text(image, participant['name'], position=(400, 250), font_size=50)
    draw_text(image, event_title, position=(400, 350), font_size=30)
    draw_text(image, participant.get('date', datetime.today().strftime("%Y-%m-%d")), position=(400, 450), font_size=25)
    
    # Save as PDF
    name_safe = participant['name'].replace(" ", "_")
    pdf_path = os.path.join(output_dir, f"{name_safe}.pdf")
    image.save(pdf_path, "PDF", resolution=100.0)
    print(f"Generated certificate: {pdf_path}")

# ------------------------
# CLI Functions
# ------------------------
def create_event(args):
    event_path = os.path.join(EVENTS_DIR, args.title.replace(" ", "_"))
    os.makedirs(event_path, exist_ok=True)
    print(f"Event '{args.title}' created at {event_path}")

def add_participants_csv(args):
    event_path = os.path.join(EVENTS_DIR, args.event.replace(" ", "_"))
    if not os.path.exists(event_path):
        print(f"Event '{args.event}' does not exist. Create it first.")
        return
    
    df = pd.read_csv(args.file)
    df.to_csv(os.path.join(event_path, "participants.csv"), index=False)
    print(f"Imported {len(df)} participants from {args.file}")

def generate_certificates(args):
    event_path = os.path.join(EVENTS_DIR, args.event.replace(" ", "_"))
    participants_file = os.path.join(event_path, "participants.csv")
    output_dir = os.path.join(event_path, "certificates")
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(participants_file):
        print(f"No participants found for event '{args.event}'.")
        return

    df = pd.read_csv(participants_file)
    for _, participant in df.iterrows():
        generate_certificate(participant, args.event, args.template, output_dir)

# ------------------------
# Argument Parser
# ------------------------
parser = argparse.ArgumentParser(description="Local Certificate Generator CLI")
subparsers = parser.add_subparsers()

# Create event
parser_event = subparsers.add_parser("create-event")
parser_event.add_argument("--title", required=True)
parser_event.set_defaults(func=create_event)

# Add participants via CSV
parser_part = subparsers.add_parser("add-participants-csv")
parser_part.add_argument("--event", required=True)
parser_part.add_argument("--file", required=True)
parser_part.set_defaults(func=add_participants_csv)

# Generate certificates
parser_gen = subparsers.add_parser("generate")
parser_gen.add_argument("--event", required=True)
parser_gen.add_argument("--template", default="default_template.png")
parser_gen.set_defaults(func=generate_certificates)

# ------------------------
# Main
# ------------------------
if __name__ == "__main__":
    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()
