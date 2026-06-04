import io
import os
from typing import Optional

from config import BADGES
from database import get_user_stats, get_user_badges, add_achievement

# Unicode (o'zbek lotin + kirill) shriftlarni turli OS'larda topish
_FONT_CANDIDATES = [
    # Bundled custom fonts (highest priority for production portability)
    (os.path.join("data", "font.ttf"), os.path.join("data", "font_bold.ttf")),
    # Windows
    (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
    (r"C:\Windows\Fonts\verdana.ttf", r"C:\Windows\Fonts\verdanab.ttf"),
    # Linux (Debian/Ubuntu)
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    # Linux (boshqa joylashuv)
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    # macOS
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf",
     "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
]

_REGISTERED = {"done": False, "regular": "Helvetica", "bold": "Helvetica-Bold"}


def _register_unicode_font():
    """Birinchi mavjud Unicode shriftni reportlab'ga ro'yxatdan o'tkazadi."""
    if _REGISTERED["done"]:
        return _REGISTERED["regular"], _REGISTERED["bold"]
    _REGISTERED["done"] = True

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        return _REGISTERED["regular"], _REGISTERED["bold"]

    for regular_path, bold_path in _FONT_CANDIDATES:
        if os.path.exists(regular_path):
            try:
                pdfmetrics.registerFont(TTFont("UZSLFont", regular_path))
                _REGISTERED["regular"] = "UZSLFont"
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont("UZSLFont-Bold", bold_path))
                    _REGISTERED["bold"] = "UZSLFont-Bold"
                else:
                    _REGISTERED["bold"] = "UZSLFont"
                break
            except Exception:
                continue

    return _REGISTERED["regular"], _REGISTERED["bold"]


async def check_and_award_badge(user_id: int):
    """Foydalanuvchi yangi badge olgan bo'lsa, uni qaytaradi (aks holda None)."""
    stats = await get_user_stats(user_id)
    approved = stats["approved"] or 0

    existing = await get_user_badges(user_id)

    for threshold, (emoji, name, has_certificate) in sorted(BADGES.items()):
        if approved >= threshold and name not in existing:
            await add_achievement(user_id, name)
            return {
                "emoji": emoji,
                "name": name,
                "threshold": threshold,
                "has_certificate": has_certificate,
            }
    return None


def generate_certificate(full_name: str, badge_name: str, video_count: int) -> Optional[io.BytesIO]:
    """UZSL hissa qo'shuvchi uchun PDF sertifikat yaratadi.

    reportlab o'rnatilmagan bo'lsa, None qaytaradi.
    Unicode shrift topilsa, o'zbek/kirill harflari to'g'ri chiqadi.
    """
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.pdfgen import canvas as pdf_canvas
    except ImportError:
        return None

    font_regular, font_bold = _register_unicode_font()

    buf = io.BytesIO()
    width, height = landscape(A4)
    c = pdf_canvas.Canvas(buf, pagesize=landscape(A4))

    # Tashqi ramka
    c.setStrokeColor(colors.HexColor("#673AB7"))
    c.setLineWidth(4)
    c.rect(1 * cm, 1 * cm, width - 2 * cm, height - 2 * cm)
    # Ichki nozik ramka
    c.setStrokeColor(colors.HexColor("#B39DDB"))
    c.setLineWidth(1)
    c.rect(1.3 * cm, 1.3 * cm, width - 2.6 * cm, height - 2.6 * cm)

    # Sarlavha
    c.setFillColor(colors.HexColor("#673AB7"))
    c.setFont(font_bold, 38)
    c.drawCentredString(width / 2, height - 4 * cm, "SERTIFIKAT")

    c.setFillColor(colors.black)
    c.setFont(font_regular, 16)
    c.drawCentredString(
        width / 2, height - 5.6 * cm,
        "Ushbu sertifikat quyidagi shaxsga taqdim etiladi:",
    )

    # Ism
    c.setFillColor(colors.HexColor("#311B92"))
    c.setFont(font_bold, 28)
    c.drawCentredString(width / 2, height - 8 * cm, full_name)

    # Tavsif
    c.setFillColor(colors.black)
    c.setFont(font_regular, 16)
    c.drawCentredString(
        width / 2, height - 9.5 * cm,
        "O'zbek imo-ishora tili (UZSL) dataset loyihasiga",
    )
    c.drawCentredString(
        width / 2, height - 10.3 * cm,
        "qo'shgan munosib hissasi uchun.",
    )

    # Daraja va son
    c.setFont(font_bold, 16)
    c.drawCentredString(width / 2, height - 12 * cm, f"Daraja: {badge_name}")
    c.setFont(font_regular, 14)
    c.drawCentredString(
        width / 2, height - 12.9 * cm,
        f"Tasdiqlangan videolar: {video_count} ta",
    )

    # Pastki izoh
    c.setFillColor(colors.HexColor("#555555"))
    c.setFont(font_regular, 11)
    c.drawCentredString(
        width / 2, 2 * cm,
        "UZSL Tarjimon loyihasi  •  kar va soqovlar uchun",
    )

    c.showPage()
    c.save()
    buf.seek(0)
    return buf
