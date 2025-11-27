# pozicijos/thumbnails.py
import io
import os
from typing import Optional

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont

THUMB_SIZE = (400, 400)  # normalus dydis JPG/PDF miniatiūroms


def _make_placeholder(label: str, size=THUMB_SIZE,
                      bg=(240, 240, 240), fg=(60, 60, 60)) -> Image.Image:
    img = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(img)
    text = (label or "").upper() or "FILE"
    font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (size[0] - w) // 2
    y = (size[1] - h) // 2
    draw.text((x, y), text, font=font, fill=fg)
    return img


def _image_to_png_content(img: Image.Image) -> ContentFile:
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    img.thumbnail(THUMB_SIZE, Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ContentFile(buf.read())


def generate_brezinys_thumbnail(brezinys, force: bool = False) -> Optional[bool]:
    """
    JPG/PNG/TIFF/PDF → PNG thumbnail į brezinys.preview.
    STP/STEP čia neliečiam – jiems naudosim statinę ikoną šablone.
    """
    file_field = getattr(brezinys, "failas", None)
    if not file_field:
        return None

    if brezinys.preview and not force:
        return None

    name = file_field.name or ""
    ext = os.path.splitext(name)[1].lower()

    # 🔹 STP/STEP – jokio thumbnail generavimo
    if ext in (".stp", ".step"):
        return None

    thumb_img: Optional[Image.Image] = None

    try:
        if ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff"):
            file_field.open("rb")
            img = Image.open(file_field)
            img.load()
            thumb_img = img
        elif ext == ".pdf":
            try:
                from pdf2image import convert_from_bytes  # type: ignore
            except ImportError:
                thumb_img = _make_placeholder("PDF")
            else:
                with file_field.open("rb"):
                    data = file_field.read()
                pages = convert_from_bytes(data, first_page=1, last_page=1)
                if pages:
                    thumb_img = pages[0]
                else:
                    thumb_img = _make_placeholder("PDF")
        else:
            label = ext[1:] if ext else "?"
            thumb_img = _make_placeholder(label)
    except Exception:
        thumb_img = _make_placeholder("ERR")

    if thumb_img is None:
        return False

    content = _image_to_png_content(thumb_img)
    base = os.path.splitext(os.path.basename(name))[0] or "thumb"
    file_name = f"{base}_thumb.png"

    brezinys.preview.save(file_name, content, save=False)
    brezinys.save(update_fields=["preview"])
    return True
