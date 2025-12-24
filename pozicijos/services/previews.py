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


# Bendri parametrai
THUMB_MAX_W = 1000   # generuojamo PNG maksimalus plotis (px)
THUMB_MAX_H = 1000   # generuojamo PNG maksimalus aukštis (px)
PDF_DPI = 144        # PDF rasterizavimo „dpi“ (~ kokybė vs. dydis)
PNG_QUALITY = 85     # PNG kompresija (Pillow pats parinks tinkamai)


@dataclass
class PreviewResult:
    ok: bool
    message: str = ""
    saved_path: Optional[str] = None  # media relative path (pvz., pozicijos/.../previews/name.png)


def _pil_to_png_bytes(img: Image.Image) -> bytes:
    # konvertuojam į RGB (saugiau) ir sumažinam iki THUMB_MAX_*
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((THUMB_MAX_W, THUMB_MAX_H), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _save_preview(b: PozicijosBrezinys, png_bytes: bytes) -> PreviewResult:
    rel = b._preview_relpath()  # pvz. pozicijos/breziniai/previews/<vardas>.png
    storage = b.failas.storage

    # užtikrinam katalogą (jei FileSystemStorage)
    if hasattr(storage, "path"):
        try:
            abs_path = storage.path(rel)
            abs_folder = os.path.dirname(abs_path)
            os.makedirs(abs_folder, exist_ok=True)
        except Exception:
            pass

    # įrašom
    content = ContentFile(png_bytes)

    # jei buvo – perrašom
    if storage.exists(rel):
        storage.delete(rel)

    saved_name = storage.save(rel, content)

    # sinchronizuojam su ImageField (kad būtų aiškus "source of truth")
    try:
        if getattr(b, "preview", None) is not None:
            b.preview.name = saved_name
            b.save(update_fields=["preview"])
    except Exception:
        # preview failas vis tiek yra storage'e – neblokuojam
        pass

    return PreviewResult(ok=True, saved_path=saved_name)


def generate_preview_for_instance(b: PozicijosBrezinys) -> PreviewResult:
    """
    Sugeneruoja PNG 'preview' pagal b.failas:
    - PDF -> pirmas puslapis per PyMuPDF (jei įdiegtas)
    - TIFF (ir multi-page) -> pirmas kadras per Pillow
    - Dideli JPEG/PNG ir pan. -> sumažinta kopija
    - STEP/STP -> miniatiūros negeneruojam (UI rodo statinę 3D ikoną)
    - Kiti formatai -> ok=False
    """
    name_lower = (getattr(b.failas, "name", "") or "").lower()
    if not name_lower:
        return PreviewResult(ok=False, message="Nėra failo vardo")

    _, ext = os.path.splitext(name_lower)
    ext = (ext or "").lstrip(".").lower()

    # STEP/STP – miniatiūros negeneruojam (rodysim statinę ikoną)
    if ext in ("stp", "step"):
        return PreviewResult(ok=True, message="STP/STEP: rodoma 3D ikona (miniatiūra negeneruojama)")

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
            zoom = PDF_DPI / 72.0  # 72pt bazinis
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)  # be alfa
            png_bytes = pix.tobytes("png")

            # dar kartą praleidžiam per Pillow, kad unifikuotume max dydį
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
                img.seek(0)  # pirmas kadras
            except Exception:
                pass
            png_bytes = _pil_to_png_bytes(img)
            return _save_preview(b, png_bytes)
        except Exception as e:
            return PreviewResult(ok=False, message=f"TIFF preview klaida: {e}")

    # Standartiniai vaizdai – sugeneruojam sumažintą preview
    if ext in ("jpg", "jpeg", "png", "webp", "bmp", "gif"):
        try:
            b.failas.seek(0)
            img = Image.open(b.failas)
            png_bytes = _pil_to_png_bytes(img)
            return _save_preview(b, png_bytes)
        except Exception as e:
            return PreviewResult(ok=False, message=f"IMG preview klaida: {e}")

    # Kiti formatai (pvz., CAD) – kol kas nepalaikom
    return PreviewResult(ok=False, message=f"Nepalaikomas formatas: .{ext}")


def regenerate_missing_preview(b: PozicijosBrezinys) -> PreviewResult:
    """Sugeneruoja, jei nėra. Jei yra – grįžta ok=True be veiksmų."""
    # Jei STEP/STP – preview nenaudojam
    try:
        if getattr(b, "is_step", False):
            return PreviewResult(ok=True, message="STP/STEP: rodoma 3D ikona")
    except Exception:
        pass

    try:
        if getattr(b, "preview", None) and getattr(b.preview, "name", ""):
            return PreviewResult(ok=True, message="Jau yra", saved_path=b.preview.name)
    except Exception:
        pass

    storage = b.failas.storage
    rel = b._preview_relpath()
    if rel and storage.exists(rel):
        return PreviewResult(ok=True, message="Jau yra", saved_path=rel)

    return generate_preview_for_instance(b)
