import os
from typing import List, Dict
from PIL import Image, ImageDraw, ImageFont

from .helpers import resource_path, safe_filename

def load_template(template_path: str) -> Image.Image:
    if not os.path.exists(template_path):
        return Image.new("RGB", (1600, 1000), color="white")
    return Image.open(template_path).convert("RGB")

def draw_text(image: Image.Image, text: str, position: tuple, font_size: int = 40) -> None:
    draw = ImageDraw.Draw(image)
    font_path = resource_path(os.path.join("fonts", "Roboto-VariableFont_wdth,wght.ttf"))
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.load_default()

    text = "" if text is None else str(text)
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = position[0] - (w / 2)
    y = position[1] - (h / 2)
    draw.text((x, y), text, fill="black", font=font)

def generate_certificate(
    participant_name: str,
    event_title: str,
    event_org: str,
    event_dates: str,
    template_path: str,
    output_dir: str,
    signatories: List[Dict],
) -> str:
    image = load_template(template_path)
    img_w, img_h = image.size

    # NOTE: Keep your original coordinates (adjust per template if needed)
    draw_text(image, participant_name, position=(1000, 680), font_size=70)
    draw_text(image, f"for participating in the {event_title} held by {event_org}", position=(1000, 830), font_size=32)
    draw_text(image, f"on {event_dates}", position=(1000, 900), font_size=32)

    bottom_signature_y = img_h - 210
    bottom_name_y = img_h - 140
    bottom_position_y = img_h - 90

    for i, sig in enumerate(signatories):
        if len(signatories) == 1:
            x = img_w // 2
        elif len(signatories) == 2:
            x = img_w // 3 if i == 0 else 2 * img_w // 3
        else:
            x = img_w // 4 if i == 0 else img_w // 2 if i == 1 else 3 * img_w // 4

        sig_path = sig.get("signature_path")
        if sig_path and os.path.exists(sig_path):
            s_img = Image.open(sig_path).convert("RGBA")
            max_width = int(img_w * 0.18)
            ratio = max_width / max(1, s_img.width)
            new_height = int(s_img.height * ratio)
            s_img = s_img.resize((max_width, new_height))
            sig_x = x - s_img.width // 2
            sig_y = bottom_signature_y - new_height // 2
            image.paste(s_img, (sig_x, sig_y), s_img)

        draw_text(image, sig.get("name", ""), position=(x, bottom_name_y), font_size=40)
        draw_text(image, sig.get("position", ""), position=(x, bottom_position_y), font_size=32)

    os.makedirs(output_dir, exist_ok=True)
    pdf_name = safe_filename(participant_name) + ".pdf"
    pdf_path = os.path.join(output_dir, pdf_name)
    image.save(pdf_path, "PDF", resolution=100.0)
    return pdf_path
