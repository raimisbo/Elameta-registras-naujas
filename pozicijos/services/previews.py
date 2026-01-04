# pozicijos/services/previews.py
from __future__ import annotations

import io
import os
from dataclasses import dataclass
from typing import Optional

from django.core.files.base import ContentFile

from PIL import Image

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

from ..models import PozicijosBrezinys


THUMB_MAX_W = 1000
THUMB_MAX_H = 1000
PDF_DPI = 144


@dataclass
class PreviewResult:
    ok: bool
    message: str = ""
    saved_path: Optional[str] = None


def _pil_to_png_bytes(img: Image.Image) -> bytes:
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((THUMB_MAX_W, THUMB_MAX_H), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _safe_preview_relpath(b: PozicijosBrezinys) -> str:
    """
    Apsauga: jei kažkada vėl dings helperis modelyje – nebelūžtam.
    """
    try:
        rel = b._preview_relpath()
        if rel:
            return rel
    except Exception:
        pass
    pk = b.pk or "tmp"
    return f"pozicijos/breziniai/previews/brezinys-{pk}.png"


def _save_preview(b: PozicijosBrezinys, png_bytes: bytes) -> PreviewResult:
    rel = _safe_preview_relpath(b)
    storage = b.failas.storage

    if hasattr(storage, "path"):
        try:
            abs_path = storage.path(rel)
            abs_folder = os.path.dirname(abs_path)
            os.makedirs(abs_folder, exist_ok=True)
        except Exception:
            pass

    content = ContentFile(png_bytes)
    if storage.exists(rel):
        storage.delete(rel)
    saved_name = storage.save(rel, content)

    try:
        if getattr(b, "preview", None) is not None:
            b.preview.name = saved_name
            b.save(update_fields=["preview"])
    except Exception:
        pass

    return PreviewResult(ok=True, saved_path=saved_name)


def generate_preview_for_instance(b: PozicijosBrezinys) -> PreviewResult:
    """
    PNG preview pagal b.failas:
    - PDF -> pirmas puslapis per PyMuPDF
    - TIFF -> pirmas kadras per Pillow
    - JPG/PNG/... -> sumažinta kopija
    - STEP/STP -> NEGENERUOJAM (rodysim statinę 3D ikoną šablone)
    """
    name_lower = (getattr(b.failas, "name", "") or "").lower()
    if not name_lower:
        return PreviewResult(ok=False, message="Nėra failo vardo")

    _, ext = os.path.splitext(name_lower)
    ext = (ext or "").lstrip(".").lower()

    # STEP/STP – specialiai nenaudojam preview
    if ext in ("stp", "step"):
        return PreviewResult(ok=True, message="STEP/STP: preview nenaudojama", saved_path=None)

    # PDF
    if ext == "pdf":
        if not fitz:
            return PreviewResult(ok=False, message="PyMuPDF neįdiegtas – PDF peržiūra negalima")
        try:
            stream = b.failas.open("rb").read()
            doc = fitz.open(stream=stream, filetype="pdf")
            if doc.page_count == 0:
                return PreviewResult(ok=False, message="PDF tuščias")
            page = doc.load_page(0)
            zoom = PDF_DPI / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            png_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(png_bytes))
            png_bytes = _pil_to_png_bytes(img)
            return _save_preview(b, png_bytes)
        except Exception as e:
            return PreviewResult(ok=False, message=f"PDF preview klaida: {e}")

    # TIFF
    if ext in ("tif", "tiff"):
        try:
            b.failas.seek(0)
            img = Image.open(b.failas)
            try:
                img.seek(0)
            except Exception:
                pass
            png_bytes = _pil_to_png_bytes(img)
            return _save_preview(b, png_bytes)
        except Exception as e:
            return PreviewResult(ok=False, message=f"TIFF preview klaida: {e}")

    # Standartiniai vaizdai
    if ext in ("jpg", "jpeg", "png", "webp", "bmp", "gif"):
        try:
            b.failas.seek(0)
            img = Image.open(b.failas)
            png_bytes = _pil_to_png_bytes(img)
            return _save_preview(b, png_bytes)
        except Exception as e:
            return PreviewResult(ok=False, message=f"IMG preview klaida: {e}")

    return PreviewResult(ok=False, message=f"Nepalaikomas formatas: .{ext}")


def regenerate_missing_preview(b: PozicijosBrezinys) -> PreviewResult:
    """
    Sugeneruoja, jei nėra.
    STEP/STP atveju laikom ok=True (nes preview sąmoningai nenaudojam).
    """
    if getattr(b, "is_step", False):
        return PreviewResult(ok=True, message="STEP/STP: preview nenaudojama", saved_path=None)

    try:
        if getattr(b, "preview", None) and getattr(b.preview, "name", ""):
            return PreviewResult(ok=True, message="Jau yra", saved_path=b.preview.name)
    except Exception:
        pass

    storage = b.failas.storage
    rel = _safe_preview_relpath(b)
    if rel and storage.exists(rel):
        return PreviewResult(ok=True, message="Jau yra", saved_path=rel)

    return generate_preview_for_instance(b)
