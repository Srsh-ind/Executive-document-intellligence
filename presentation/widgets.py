from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE
from pptx.dml.color import RGBColor


def rgb(hex_color):
    hex_color = hex_color.replace("#", "")
    return RGBColor(
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16)
    )
def fit_text(text, max_chars=150):
    text = str(text or "").strip()

    if len(text) <= max_chars:
        return text

    text = text[:max_chars]
    last_space = text.rfind(" ")

    if last_space > 0:
        text = text[:last_space]

    return text + "..."


def set_text_style(shape, font_size=14, bold=False, color="111827"):
    frame = shape.text_frame

    for paragraph in frame.paragraphs:
        paragraph.alignment = PP_ALIGN.LEFT

        for run in paragraph.runs:
            run.font.size = Pt(font_size)
            run.font.bold = bold
            run.font.color.rgb = rgb(color)


def add_textbox(slide, text, x, y, w, h, font_size=16, bold=False, color="111827"):
    box = slide.shapes.add_textbox(
        Inches(x), Inches(y), Inches(w), Inches(h)
    )

    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE

    paragraph = frame.paragraphs[0]
    paragraph.text = str(text or "")
    paragraph.alignment = PP_ALIGN.LEFT

    run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = rgb(color)

    return box

def add_title(slide, title, theme, x=0.65, y=0.35, w=12, h=0.6):
    colors = theme["colors"]

    return add_textbox(
        slide,
        title,
        x,
        y,
        w,
        h,
        font_size=28,
        bold=True,
        color=colors["text"]
    )


def add_subtitle(slide, text, theme, x=0.65, y=1.0, w=11.8, h=0.45):
    colors = theme["colors"]

    return add_textbox(
        slide,
        text,
        x,
        y,
        w,
        h,
        font_size=14,
        bold=False,
        color=colors["subtext"]
    )


def add_background(slide, theme):
    colors = theme["colors"]

    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = rgb(colors["background"])


def add_card(slide, title, body, theme, x, y, w, h):
    colors = theme["colors"]

    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(h)
    )

    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(colors["surface"])
    shape.line.color.rgb = rgb(colors["primary"])

    shape.text = ""

    title = fit_text(title, 55)
    body = fit_text(body, 150)


    
    add_textbox(
        slide,
        title,
        x + 0.18,
        y + 0.15,
        w - 0.35,
        0.35,
        font_size=14,
        bold=True,
        color=colors["text"]
    )

    add_textbox(
        slide,
        body,
        x + 0.18,
        y + 0.58,
        w - 0.35,
        h - 0.75,
        font_size=12,
        bold=False,
        color=colors["subtext"]
    )

    return shape


def add_kpi_card(slide, label, value, note, theme, x, y, w, h):
    colors = theme["colors"]

    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(h)
    )

    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(colors["surface"])
    shape.line.color.rgb = rgb(colors["secondary"])

    add_textbox(
        slide,
        label,
        x + 0.18,
        y + 0.15,
        w - 0.35,
        0.3,
        font_size=11,
        bold=False,
        color=colors["subtext"]
    )

    add_textbox(
        slide,
        value,
        x + 0.18,
        y + 0.48,
        w - 0.35,
        0.45,
        font_size=24,
        bold=True,
        color=colors["accent"]
    )

    add_textbox(
        slide,
        note,
        x + 0.18,
        y + 1.0,
        w - 0.35,
        h - 1.1,
        font_size=10,
        bold=False,
        color=colors["subtext"]
    )

    return shape


def add_section_label(slide, text, theme, x, y, w=2.4, h=0.35):
    colors = theme["colors"]

    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(h)
    )

    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(colors["accent"])
    shape.line.color.rgb = rgb(colors["accent"])

    shape.text = text
    set_text_style(shape, font_size=10, bold=True, color="FFFFFF")

    return shape


def add_bullet_list(slide, items, theme, x, y, w, h, font_size=13):
    colors = theme["colors"]

    box = slide.shapes.add_textbox(
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(h)
    )

    frame = box.text_frame
    frame.clear()

    for item in items:
        paragraph = frame.add_paragraph()
        paragraph.text = str(item)
        paragraph.level = 0
        paragraph.font.size = Pt(font_size)
        paragraph.font.color.rgb = rgb(colors["subtext"])

    return box


def add_metric_strip(slide, cards, theme, x=0.65, y=1.35, w=12.0, h=1.15):
    if not cards:
        return

    gap = 0.18
    count = min(len(cards), 4)
    card_w = (w - gap * (count - 1)) / count

    for i, card in enumerate(cards[:count]):
        cx = x + i * (card_w + gap)

        label = card.get("name") or card.get("label") or "Metric"
        value = card.get("value", "")
        note = card.get("interpretation") or card.get("note") or ""

        add_kpi_card(
            slide,
            label,
            value,
            note,
            theme,
            cx,
            y,
            card_w,
            h
        )


def add_progress_bar(slide, label, value, theme, x, y, w, h=0.28):
    colors = theme["colors"]

    try:
        numeric = float(str(value).replace("%", "").strip())
    except Exception:
        numeric = 0

    numeric = max(0, min(numeric, 100))

    add_textbox(
        slide,
        label,
        x,
        y - 0.25,
        w,
        0.25,
        font_size=10,
        bold=True,
        color=colors["text"]
    )

    bg = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(h)
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = rgb(colors["surface"])
    bg.line.color.rgb = rgb(colors["surface"])

    fg = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x),
        Inches(y),
        Inches(w * numeric / 100),
        Inches(h)
    )
    fg.fill.solid()
    fg.fill.fore_color.rgb = rgb(colors["accent"])
    fg.line.color.rgb = rgb(colors["accent"])

    add_textbox(
        slide,
        f"{numeric:.0f}%",
        x + w - 0.65,
        y - 0.02,
        0.6,
        0.25,
        font_size=9,
        bold=True,
        color=colors["text"]
    )


def add_status_card(slide, label, title, note, theme, x, y, w, h, status="neutral"):
    colors = theme["colors"]

    status_color = colors["primary"]

    if status == "risk":
        status_color = colors["danger"]
    elif status == "success":
        status_color = colors["success"]
    elif status == "action":
        status_color = colors["accent"]

    label = fit_text(label, 35)
    title = fit_text(title, 90)
    note = fit_text(note, 120)

    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(h)
    )

    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(colors["surface"])
    shape.line.color.rgb = rgb(status_color)

    add_section_label(slide, label, theme, x + 0.18, y + 0.15, w=1.2, h=0.28)

    add_textbox(
        slide,
        title,
        x + 0.18,
        y + 0.55,
        w - 0.35,
        0.4,
        font_size=14,
        bold=True,
        color=colors["text"]
    )

    add_textbox(
        slide,
        note,
        x + 0.18,
        y + 1.0,
        w - 0.35,
        h - 1.1,
        font_size=12,
        bold=False,
        color=colors["subtext"]
    )

    return shape


def add_footer(slide, theme, page=None):
    colors = theme["colors"]

    text = "Executive Insight Generator"

    if page:
        text = f"{text}  |  {page}"

    add_textbox(
        slide,
        text,
        0.65,
        7.05,
        12,
        0.25,
        font_size=9,
        bold=False,
        color=colors["subtext"]
    )
