from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OVERLEAF_DIR = ROOT / "report" / "overleaf"


WHITE = "#F7F8FB"
INK = "#172033"
MUTED = "#5D677A"
BORDER = "#D6DCE8"
PRIMARY = "#1D4ED8"
PRIMARY_LIGHT = "#DBEAFE"
GREEN = "#059669"
GREEN_LIGHT = "#D1FAE5"
AMBER = "#D97706"
AMBER_LIGHT = "#FEF3C7"
PURPLE = "#7C3AED"
PURPLE_LIGHT = "#EDE9FE"
GRAY_LIGHT = "#EEF2F7"


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        ("arialbd.ttf" if bold else "arial.ttf"),
        ("seguisb.ttf" if bold else "segoeui.ttf"),
        ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


TITLE_FONT = load_font(34, bold=True)
SUBTITLE_FONT = load_font(20)
BOX_TITLE_FONT = load_font(24, bold=True)
BODY_FONT = load_font(18)
SMALL_FONT = load_font(16)


def rounded_box(draw: ImageDraw.ImageDraw, box, fill, outline=BORDER, radius=26, width=3):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_text_block(draw: ImageDraw.ImageDraw, box, title: str, lines: list[str], fill=INK, title_fill=INK):
    x1, y1, x2, y2 = box
    draw.text((x1 + 24, y1 + 16), title, font=BOX_TITLE_FONT, fill=title_fill)
    y = y1 + 58
    for line in lines:
        draw.text((x1 + 24, y), line, font=BODY_FONT, fill=fill)
        y += 28


def draw_arrow(draw: ImageDraw.ImageDraw, start, end, fill=INK, width=5):
    draw.line([start, end], fill=fill, width=width)
    ex, ey = end
    sx, sy = start
    if abs(ex - sx) >= abs(ey - sy):
        direction = 1 if ex > sx else -1
        head = [(ex, ey), (ex - 18 * direction, ey - 10), (ex - 18 * direction, ey + 10)]
    else:
        direction = 1 if ey > sy else -1
        head = [(ex, ey), (ex - 10, ey - 18 * direction), (ex + 10, ey - 18 * direction)]
    draw.polygon(head, fill=fill)


def draw_center_title(img: Image.Image, title: str, subtitle: str):
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), title, font=TITLE_FONT)
    title_x = (img.width - (bbox[2] - bbox[0])) // 2
    draw.text((title_x, 28), title, font=TITLE_FONT, fill=INK)
    bbox = draw.textbbox((0, 0), subtitle, font=SUBTITLE_FONT)
    subtitle_x = (img.width - (bbox[2] - bbox[0])) // 2
    draw.text((subtitle_x, 78), subtitle, font=SUBTITLE_FONT, fill=MUTED)


def save_architecture_diagram():
    img = Image.new("RGB", (1800, 1100), WHITE)
    draw = ImageDraw.Draw(img)
    draw_center_title(img, "NexRag High-Level Architecture", "Hybrid evidence routing for academic question answering")

    ui = (100, 180, 420, 410)
    api = (500, 180, 820, 410)
    router = (900, 120, 1220, 300)
    rag = (900, 360, 1220, 580)
    kg = (1300, 120, 1620, 300)
    llm = (1300, 360, 1620, 580)
    docs = (900, 700, 1220, 920)
    ttl = (1300, 700, 1620, 920)
    ops = (500, 700, 820, 920)

    rounded_box(draw, ui, PRIMARY_LIGHT)
    draw_text_block(draw, ui, "React Frontend", ["Chat interface", "Source evidence panel", "Knowledge graph editor"], title_fill=PRIMARY)

    rounded_box(draw, api, WHITE)
    draw_text_block(draw, api, "FastAPI Backend", ["Request orchestration", "Status and upload APIs", "Streaming response assembly"])

    rounded_box(draw, router, AMBER_LIGHT)
    draw_text_block(draw, router, "Query Router", ["Intent detection", "KG / vector / combined path", "Confidence policy"], title_fill=AMBER)

    rounded_box(draw, rag, GREEN_LIGHT)
    draw_text_block(draw, rag, "Retrieval Engine", ["PDF parsing with pdfplumber", "Dense embeddings + FAISS", "BM25 + cross-encoder reranking"], title_fill=GREEN)

    rounded_box(draw, kg, PURPLE_LIGHT)
    draw_text_block(draw, kg, "Knowledge Graph", ["Fuseki SPARQL endpoint", "Faculty, course, regulation facts", "TTL validation and query support"], title_fill=PURPLE)

    rounded_box(draw, llm, PRIMARY_LIGHT)
    draw_text_block(draw, llm, "Local LLM", ["Ollama runtime", "Grounded prompt construction", "Response synthesis"], title_fill=PRIMARY)

    rounded_box(draw, docs, WHITE)
    draw_text_block(draw, docs, "Academic PDFs", ["Handbook", "Seminar guidelines", "Project report format", "Syllabus and circulars"])

    rounded_box(draw, ttl, WHITE)
    draw_text_block(draw, ttl, "RDF / TTL Sources", ["mesitam_data.ttl", "university_faq.ttl", "merged_kg.ttl"])

    rounded_box(draw, ops, GRAY_LIGHT)
    draw_text_block(draw, ops, "Operational Support", ["History logging", "System status", "Document management"], fill=MUTED)

    draw_arrow(draw, (420, 295), (500, 295))
    draw_arrow(draw, (820, 240), (900, 210))
    draw_arrow(draw, (820, 350), (900, 460))
    draw_arrow(draw, (1220, 210), (1300, 210))
    draw_arrow(draw, (1220, 460), (1300, 460))
    draw_arrow(draw, (1060, 700), (1060, 580))
    draw_arrow(draw, (1460, 700), (1460, 580))
    draw_arrow(draw, (820, 810), (1060, 810))
    draw_arrow(draw, (820, 840), (1460, 840))
    draw_arrow(draw, (1300, 500), (820, 500))
    draw_arrow(draw, (900, 500), (820, 500))
    draw_arrow(draw, (820, 500), (820, 350))
    draw_arrow(draw, (660, 410), (660, 700))

    img.save(OVERLEAF_DIR / "nexrag_architecture.png")


def save_query_flow_diagram():
    img = Image.new("RGB", (1800, 900), WHITE)
    draw = ImageDraw.Draw(img)
    draw_center_title(img, "End-to-End Query Processing Flow", "From user question to grounded response with evidence visibility")

    steps = [
        ("1. User Query", "Natural-language academic question", PRIMARY_LIGHT, PRIMARY),
        ("2. Intent Routing", "Detect faculty / regulation / definition / general intent", AMBER_LIGHT, AMBER),
        ("3. Evidence Retrieval", "Knowledge graph lookup and hybrid PDF retrieval", GREEN_LIGHT, GREEN),
        ("4. Evidence Fusion", "Rank snippets, attach graph facts, estimate confidence", PURPLE_LIGHT, PURPLE),
        ("5. Local Generation", "Prompt Ollama with bounded academic context", PRIMARY_LIGHT, PRIMARY),
        ("6. UI Response", "Answer, route badge, confidence, and sources", WHITE, INK),
    ]

    x = 110
    y = 220
    w = 240
    h = 210
    gap = 40
    boxes = []
    for index, (title, body, fill, accent) in enumerate(steps):
        box = (x + index * (w + gap), y, x + index * (w + gap) + w, y + h)
        boxes.append(box)
        rounded_box(draw, box, fill)
        draw.text((box[0] + 18, box[1] + 18), title, font=BOX_TITLE_FONT, fill=accent)
        draw.text((box[0] + 18, box[1] + 82), body, font=BODY_FONT, fill=INK)

    for left, right in zip(boxes, boxes[1:]):
        draw_arrow(draw, (left[2], (left[1] + left[3]) // 2), (right[0], (right[1] + right[3]) // 2))

    note_box = (270, 560, 1540, 760)
    rounded_box(draw, note_box, GRAY_LIGHT)
    draw.text((note_box[0] + 24, note_box[1] + 22), "Routing Outcomes", font=BOX_TITLE_FONT, fill=INK)
    notes = [
        "Knowledge Graph Mode: structured fact answers with exact entity relations.",
        "Vector Search Mode: passage-grounded answers for handbook and guideline queries.",
        "Combined Mode: graph facts reinforced by document evidence and local generation.",
        "No-hit Fallback: the system returns uncertainty instead of fabricated academic guidance.",
    ]
    yy = note_box[1] + 72
    for note in notes:
        draw.text((note_box[0] + 28, yy), f"- {note}", font=BODY_FONT, fill=MUTED)
        yy += 34

    img.save(OVERLEAF_DIR / "nexrag_query_flow.png")


def save_kg_workflow_diagram():
    img = Image.new("RGB", (1800, 950), WHITE)
    draw = ImageDraw.Draw(img)
    draw_center_title(img, "Knowledge Graph Maintenance Workflow", "Controlled update path for Turtle source validation and Fuseki refresh")

    boxes = {
        "editor": (120, 220, 420, 420),
        "inspect": (520, 220, 850, 420),
        "decision": (950, 245, 1170, 395),
        "save": (1270, 130, 1600, 310),
        "review": (1270, 360, 1600, 540),
        "restart": (1270, 610, 1600, 790),
        "query": (520, 610, 850, 790),
        "users": (120, 610, 420, 790),
    }

    rounded_box(draw, boxes["editor"], PRIMARY_LIGHT)
    draw_text_block(draw, boxes["editor"], "KG Editor UI", ["Load .ttl files", "Edit entities and relations", "Submit Validate & Save"], title_fill=PRIMARY)

    rounded_box(draw, boxes["inspect"], GREEN_LIGHT)
    draw_text_block(draw, boxes["inspect"], "TTL Inspection", ["Parse Turtle content", "Check syntax validity", "Detect removed triples"], title_fill=GREEN)

    draw.polygon([(1060, 245), (1170, 320), (1060, 395), (950, 320)], fill=AMBER_LIGHT, outline=BORDER)
    draw.text((990, 300), "Deletion\nwarning?", font=BOX_TITLE_FONT, fill=AMBER)

    rounded_box(draw, boxes["save"], WHITE)
    draw_text_block(draw, boxes["save"], "Safe Save Path", ["Persist updated source file", "Merge graph inputs", "Keep query service consistent"])

    rounded_box(draw, boxes["review"], PURPLE_LIGHT)
    draw_text_block(draw, boxes["review"], "Review Required", ["Show removed triple preview", "Ask user confirmation", "Block accidental destructive edits"], title_fill=PURPLE)

    rounded_box(draw, boxes["restart"], GREEN_LIGHT)
    draw_text_block(draw, boxes["restart"], "Fuseki Refresh", ["Regenerate merged_kg.ttl", "Restart graph endpoint", "Expose updated SPARQL facts"], title_fill=GREEN)

    rounded_box(draw, boxes["query"], GRAY_LIGHT)
    draw_text_block(draw, boxes["query"], "Graph Queries", ["Faculty / course lookup", "Definition and regulation facts", "Ready for hybrid answers"], fill=MUTED)

    rounded_box(draw, boxes["users"], WHITE)
    draw_text_block(draw, boxes["users"], "Academic Users", ["Students ask policy queries", "Faculty inspect sources", "Administrators maintain graph"], fill=MUTED)

    draw_arrow(draw, (420, 320), (520, 320))
    draw_arrow(draw, (850, 320), (950, 320))
    draw_arrow(draw, (1170, 290), (1270, 220))
    draw_arrow(draw, (1170, 350), (1270, 450))
    draw_arrow(draw, (1435, 310), (1435, 360))
    draw_arrow(draw, (1435, 540), (1435, 610))
    draw_arrow(draw, (1270, 700), (850, 700))
    draw_arrow(draw, (520, 700), (420, 700))

    draw.text((1190, 232), "No", font=SMALL_FONT, fill=MUTED)
    draw.text((1190, 438), "Yes", font=SMALL_FONT, fill=MUTED)

    img.save(OVERLEAF_DIR / "nexrag_kg_workflow.png")


def save_dfd_diagram():
    img = Image.new("RGB", (1850, 1050), WHITE)
    draw = ImageDraw.Draw(img)
    draw_center_title(img, "Data Flow Diagram for NexRag", "Level-1 view of query handling, evidence stores, and response logging")

    users = (80, 300, 340, 520)
    frontend = (450, 300, 780, 520)
    backend = (910, 220, 1250, 430)
    logs = (910, 610, 1250, 820)
    kg_store = (1410, 150, 1740, 360)
    vector_store = (1410, 430, 1740, 640)
    llm = (1410, 710, 1740, 920)

    rounded_box(draw, users, WHITE)
    draw_text_block(draw, users, "Users", ["Students", "Faculty", "Project teams"], fill=MUTED)

    rounded_box(draw, frontend, PRIMARY_LIGHT)
    draw_text_block(draw, frontend, "Frontend Interface", ["Message input", "History and document sidebar", "Sources and system status"], title_fill=PRIMARY)

    rounded_box(draw, backend, GREEN_LIGHT)
    draw_text_block(draw, backend, "FastAPI + Router", ["Intent detection", "KG + RAG orchestration", "Confidence and response payload"], title_fill=GREEN)

    rounded_box(draw, logs, GRAY_LIGHT)
    draw_text_block(draw, logs, "Logs / History", ["Question", "Answer", "Intent", "Latency"], fill=MUTED)

    rounded_box(draw, kg_store, PURPLE_LIGHT)
    draw_text_block(draw, kg_store, "Knowledge Graph Store", ["Fuseki dataset", "TTL entities", "SPARQL lookup"], title_fill=PURPLE)

    rounded_box(draw, vector_store, WHITE)
    draw_text_block(draw, vector_store, "Vector + BM25 Store", ["FAISS index", "Chunk metadata", "Ranked evidence passages"])

    rounded_box(draw, llm, PRIMARY_LIGHT)
    draw_text_block(draw, llm, "Local LLM Service", ["Ollama model", "Grounded prompt input", "Final answer synthesis"], title_fill=PRIMARY)

    draw_arrow(draw, (340, 410), (450, 410))
    draw_arrow(draw, (780, 410), (910, 325))
    draw_arrow(draw, (1250, 280), (1410, 250))
    draw_arrow(draw, (1250, 360), (1410, 535))
    draw_arrow(draw, (1250, 400), (1410, 815))
    draw_arrow(draw, (1580, 360), (1250, 360))
    draw_arrow(draw, (1410, 560), (1250, 560))
    draw_arrow(draw, (1410, 815), (1250, 815))
    draw_arrow(draw, (1080, 430), (1080, 610))
    draw_arrow(draw, (910, 715), (780, 715))
    draw_arrow(draw, (780, 715), (780, 470))

    draw.text((1285, 510), "retrieved context", font=SMALL_FONT, fill=MUTED)
    draw.text((1295, 790), "grounded answer", font=SMALL_FONT, fill=MUTED)

    img.save(OVERLEAF_DIR / "nexrag_dfd.png")


def save_mode_comparison_diagram():
    img = Image.new("RGB", (1900, 980), WHITE)
    draw = ImageDraw.Draw(img)
    draw_center_title(img, "NexRag Operating Modes", "How the system adapts to different evidence conditions")

    cards = [
        ("Knowledge Graph Mode", "Best for entity and relation questions", ["Exact faculty-course match", "Fast structured fact lookup", "High traceability"], PURPLE_LIGHT, PURPLE),
        ("Vector Search Mode", "Best for handbook and guideline questions", ["Semantic + lexical retrieval", "Ranked PDF snippets", "Good for procedural detail"], GREEN_LIGHT, GREEN),
        ("Combined Mode", "Best when graph facts and PDFs corroborate", ["Graph fact + document evidence", "Higher confidence scores", "Most informative user answer"], PRIMARY_LIGHT, PRIMARY),
        ("No-hit Fallback", "Used when strong evidence is unavailable", ["Admits uncertainty", "Avoids hallucinated policy claims", "Prompts further verification"], AMBER_LIGHT, AMBER),
    ]

    x = 90
    y = 210
    w = 390
    h = 520
    gap = 40
    for i, (title, subtitle, bullets, fill, accent) in enumerate(cards):
        box = (x + i * (w + gap), y, x + i * (w + gap) + w, y + h)
        rounded_box(draw, box, fill)
        draw.text((box[0] + 24, box[1] + 22), title, font=BOX_TITLE_FONT, fill=accent)
        draw.text((box[0] + 24, box[1] + 72), subtitle, font=BODY_FONT, fill=INK)
        yy = box[1] + 140
        for bullet in bullets:
            draw.text((box[0] + 30, yy), f"- {bullet}", font=BODY_FONT, fill=MUTED)
            yy += 50

        footer_y = box[3] - 96
        rounded_box(draw, (box[0] + 24, footer_y, box[2] - 24, box[3] - 28), WHITE, outline=fill if fill != WHITE else BORDER)
        if title == "Knowledge Graph Mode":
            footer = "Example: Who teaches Computer Graphics?"
        elif title == "Vector Search Mode":
            footer = "Example: Explain project report format"
        elif title == "Combined Mode":
            footer = "Example: What is the minimum attendance rule?"
        else:
            footer = "Example: uncommon or unsupported query"
        draw.text((box[0] + 44, footer_y + 24), footer, font=SMALL_FONT, fill=INK)

    img.save(OVERLEAF_DIR / "nexrag_mode_comparison.png")


def crop(src_name: str, dst_name: str, box):
    src = Image.open(OVERLEAF_DIR / src_name)
    cropped = src.crop(box)
    cropped.save(OVERLEAF_DIR / dst_name)


def create_panel_composite():
    sources = Image.open(OVERLEAF_DIR / "nexrag_sources_full.png")
    status = Image.open(OVERLEAF_DIR / "nexrag_system_status_full.png")
    right_box = (2550, 110, 3180, 1680)
    sources_crop = sources.crop(right_box)
    status_crop = status.crop(right_box)

    width = sources_crop.width + status_crop.width + 80
    height = max(sources_crop.height, status_crop.height) + 120
    img = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(img)
    draw.text((40, 26), "Sources and System Status Panel", font=TITLE_FONT, fill=INK)
    img.paste(sources_crop, (40, 100))
    img.paste(status_crop, (sources_crop.width + 80, 100))
    img.save(OVERLEAF_DIR / "nexrag_sources_panel.png")


def create_cropped_ui_assets():
    crop("nexrag_streaming_answer.png", "nexrag_streaming_answer_crop.png", (620, 90, 3180, 1650))
    crop("nexrag_query_attendance.png", "nexrag_query_attendance_crop.png", (620, 90, 3180, 1650))
    crop("nexrag_query_seminar.png", "nexrag_query_seminar_crop.png", (620, 90, 3180, 1650))
    create_panel_composite()


def main():
    save_architecture_diagram()
    save_query_flow_diagram()
    save_kg_workflow_diagram()
    save_dfd_diagram()
    save_mode_comparison_diagram()
    create_cropped_ui_assets()


if __name__ == "__main__":
    main()
