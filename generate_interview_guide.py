"""
==============================================================================
MODULE: generate_interview_guide.py
DESCRIPTION: Generates a comprehensive, beautifully styled PDF interview guide
             for the Product Expiry Tracking System using fpdf2 and Pillow.
==============================================================================
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF


def create_flow_diagram_image(output_path: Path) -> Path:
    """
    Renders a crisp, high-resolution architectural workflow diagram image.
    """
    width, height = 1200, 360
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Background canvas border
    draw.rectangle([5, 5, width - 5, height - 5], outline=(220, 225, 235), width=2)

    boxes = [
        {"text": "1. USER ENTRY\nManual / AI Scan", "color": (232, 240, 254), "border": (25, 118, 210), "x": 30, "y": 60, "w": 150, "h": 70},
        {"text": "2. GEMINI AI\nVision & OCR", "color": (243, 229, 245), "border": (123, 31, 162), "x": 220, "y": 60, "w": 150, "h": 70},
        {"text": "3. POSTGRESQL\nRaw SQL DB", "color": (232, 245, 233), "border": (56, 142, 60), "x": 410, "y": 60, "w": 150, "h": 70},
        {"text": "4. LIFESPAN CORE\nDays = Exp - Today", "color": (255, 248, 225), "border": (245, 124, 0), "x": 600, "y": 60, "w": 160, "h": 70},
        {"text": "5. STATUS CHECK\nExpired / Near / Safe", "color": (255, 235, 238), "border": (211, 47, 47), "x": 800, "y": 60, "w": 160, "h": 70},
        {"text": "6. ACTION TRIGGERS\nAlerts / Email Dispatch", "color": (255, 205, 210), "border": (183, 28, 28), "x": 1000, "y": 60, "w": 170, "h": 70},
    ]

    # Draw boxes
    for b in boxes:
        x, y, w, h = b["x"], b["y"], b["w"], b["h"]
        # Rounded rectangle
        draw.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=b["color"], outline=b["border"], width=2)
        # Text
        lines = b["text"].split("\n")
        draw.text((x + 15, y + 15), lines[0], fill=(20, 20, 20))
        draw.text((x + 15, y + 38), lines[1], fill=(80, 80, 80))

    # Draw arrows between boxes
    for i in range(len(boxes) - 1):
        x1 = boxes[i]["x"] + boxes[i]["w"]
        y1 = boxes[i]["y"] + boxes[i]["h"] // 2
        x2 = boxes[i + 1]["x"]
        y2 = boxes[i + 1]["y"] + boxes[i + 1]["h"] // 2
        
        draw.line([(x1 + 4, y1), (x2 - 4, y2)], fill=(100, 110, 130), width=3)
        # Arrowhead
        draw.polygon([(x2 - 4, y2), (x2 - 12, y2 - 6), (x2 - 12, y2 + 6)], fill=(100, 110, 130))

    # Bottom cycle feedback: Node 7 Checkout / Rotation back to Start
    draw.rounded_rectangle([410, 200, 770, 265], radius=8, fill=(238, 238, 238), outline=(100, 100, 100), width=2)
    draw.text((430, 215), "7. CYCLE RESOLUTION (CHECKOUT / FIFO ROTATION)", fill=(20, 20, 20))
    draw.text((430, 238), "Reduce stock on sale OR safe disposal of expired goods -> Closes Session", fill=(80, 80, 80))

    # Connecting arrows for cycle
    draw.line([(1085, 130), (1085, 232), (770, 232)], fill=(183, 28, 28), width=2)
    draw.polygon([(770, 232), (778, 227), (778, 237)], fill=(183, 28, 28))

    draw.line([(410, 232), (105, 232), (105, 130)], fill=(25, 118, 210), width=2)
    draw.polygon([(105, 130), (100, 138), (110, 138)], fill=(25, 118, 210))

    img.save(str(output_path), quality=95)
    return output_path


class InterviewPDF(FPDF):
    """
    Custom styled PDF document with header, footer, and page numbering.
    """

    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 8, "Product Expiry Tracking System - Technical Interview Preparation Guide", align="L")
            self.cell(0, 8, f"Page {self.page_no()}", align="R")
            self.ln(10)
            self.set_draw_color(220, 220, 220)
            self.line(10, 18, 200, 18)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 10, "Confidential - Prepared for Software Engineering & Full-Stack Python Technical Interviews", align="C")


def generate_pdf(pdf_path: Path, diagram_path: Path):
    pdf = InterviewPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- TITLE COVER HEADER ---
    pdf.set_fill_color(25, 118, 210)  # Primary Blue
    pdf.rect(10, 12, 190, 36, "F")

    pdf.set_xy(15, 16)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 9, "Product Expiry Tracking System", ln=True)

    pdf.set_xy(15, 26)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(225, 240, 255)
    pdf.cell(0, 7, "Comprehensive Technical & Architectural Interview Preparation Guide", ln=True)

    pdf.set_xy(15, 34)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(200, 225, 255)
    pdf.cell(0, 6, "Target: Full-Stack Python / Backend / Applied AI Engineering Roles | FMCG & Retail FIFO", ln=True)

    pdf.ln(12)

    # --- SECTION 1: PROJECT ELEVATOR PITCH ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(25, 118, 210)
    pdf.cell(0, 8, "1. Executive Summary & Project Elevator Pitch", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)
    pitch_text = (
        "How to describe the project in 30 seconds:\n"
        "'The Product Expiry Tracking System is a production-ready, full-stack inventory application "
        "designed to eradicate stock wastage and food safety risks in retail and supermarkets. "
        "It supports both manual form entry and AI-powered packaging label scanning using Google Gemini Vision, "
        "persists inventory in PostgreSQL using parameterized raw SQL queries, dynamically calculates days remaining "
        "via a mathematical lifespan engine, triggers real-time alerts with simulated urgent email broadcasts for expired "
        "or near-expiry stock, and enforces First-In, First-Out (FIFO) stock rotation through an interactive Streamlit UI.'"
    )
    pdf.multi_cell(0, 5.5, pitch_text)
    pdf.ln(3)

    # --- SECTION 2: FLOW DIAGRAM ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(25, 118, 210)
    pdf.cell(0, 8, "2. End-to-End Architectural Flow Diagram", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    # Embed flow diagram image
    if diagram_path.exists():
        pdf.image(str(diagram_path), x=10, y=pdf.get_y(), w=190)
        pdf.set_y(pdf.get_y() + 60)

    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(0, 4.5, "Figure 1: Complete 7-node architectural workflow mapping user entry, Gemini OCR, PostgreSQL database, lifespan equation evaluation, status alerts, and FIFO checkout resolution.")
    pdf.ln(4)

    # --- SECTION 3: TOP 15 INTERVIEW QUESTIONS & ANSWERS ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(25, 118, 210)
    pdf.cell(0, 8, "3. Core Technical Interview Questions & Model Answers", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    qa_list = [
        {
            "q": "Q1: What core business problem does this project solve?",
            "a": (
                "Retailers and supermarkets lose billions each year due to expired stock on shelves, leading to heavy "
                "financial losses, customer dissatisfaction, and health code penalties. Manual clipboard auditing is slow and error-prone. "
                "Our system digitizes tracking: employees scan packaging with AI vision, records are persisted in PostgreSQL, "
                "and the system alerts managers in real-time about goods nearing expiry so they can mark them down or rotate them per FIFO."
            ),
            "eg": "Example: Fresh milk arriving with a 5-day shelf life is prioritized for display ahead of newly delivered milk with a 15-day shelf life."
        },
        {
            "q": "Q2: Walk me through the mathematical Lifespan Equation and its 3 status boundaries.",
            "a": (
                "At the core is Node 5 [Calc -> StatusCheck]. It calculates:\n"
                "   Days Remaining = Expiry Date - Current Date\n"
                "The system evaluates this delta against dynamic boundary rules:\n"
                " - EXPIRED (Days Remaining <= 0): Hazard. Triggers immediate safe disposal/quarantine.\n"
                " - NEAR EXPIRY (0 < Days Remaining <= 30 Days): Warning. Triggers FIFO stock rotation and promotional discounts.\n"
                " - SAFE (Days Remaining > 30 Days): Normal. Standard shelf placement."
            ),
            "eg": "Example: If today is Oct 5, an item expiring Sept 30 has -5 days (EXPIRED). An item expiring Oct 14 has +9 days (NEAR EXPIRY)."
        },
        {
            "q": "Q3: Why did you use raw SQL with psycopg2-binary instead of an ORM like SQLAlchemy?",
            "a": (
                "Three key production reasons:\n"
                "1. Performance & Transparency: Raw SQL gives 100% control over execution plans and avoids ORM overhead.\n"
                "2. Security: We strictly used parameterized queries (%s placeholders), completely preventing SQL Injection (CWE-89).\n"
                "3. Advanced SQL Features: We leveraged native PostgreSQL 'ON CONFLICT (sku) DO UPDATE' (UPSERT), which cleanly updates stock and expiry in a single atomic database query."
            ),
            "eg": "Example: Inserting an existing SKU additively increases stock quantity instead of crashing with a duplicate key error."
        },
        {
            "q": "Q4: How does the AI Vision / OCR branch work with Google Gemini?",
            "a": (
                "In Node 3 [AI/Image Scan -> Gemini], the user uploads a photo of a packaging label or barcode. "
                "Using the official 'google-genai' SDK (model 'gemini-3.5-flash'), we transmit the image bytes with a strict JSON system prompt. "
                "Gemini analyzes the label, extracts the SKU/batch number, identifies the commercial product name and category, and normalizes the date "
                "into ISO-8601 'YYYY-MM-DD' format."
            ),
            "eg": "Example: On an Amul milk pouch, Gemini detected 'Use By: 20.07.26', batch 'BN:PH 07BM', and customer email 'customercare@amul.coop', returning clean JSON: {'sku': 'PH 07BM', 'name': 'Amul Milk', 'expiry_date': '2026-07-20'}."
        },
        {
            "q": "Q5: How do you handle AI model availability and fallback resilience?",
            "a": (
                "Production AI systems must never crash when external APIs spike or change. We implemented:\n"
                "1. Multi-Model Fallback Chain: The extractor tries 'gemini-3.5-flash', then 'gemini-3.1-flash-lite', then 'gemini-3.8-flash'.\n"
                "2. Local Heuristic OCR: If offline or API keys are missing, a deterministic regex parser extracts dates (supporting DD.MM.YY and DD/MM/YYYY) and quantities so the application remains 100% runnable offline."
            ),
            "eg": "Example: If Google's API returns 503 high-demand, the system seamlessly tries the secondary model without user disruption."
        },
        {
            "q": "Q6: What is the Dual-Engine Database Fallback feature?",
            "a": (
                "In database.py, the system first attempts to connect to PostgreSQL via psycopg2. If PostgreSQL is offline or credentials are unset, "
                "it gracefully falls back to a local SQLite database (expiry_tracker.db) with identical schema and queries. "
                "This allows a developer or reviewer to clone the repository and run it with zero setup friction."
            ),
            "eg": "Example: Running 'streamlit run app.py' immediately boots with SQLite fallback if Docker/PostgreSQL is not started yet."
        },
        {
            "q": "Q7: How does Node 6 (Action Triggers & Email Broadcast Simulation) work?",
            "a": (
                "When inventory is evaluated, if any items are EXPIRED or NEAR EXPIRY, the system triggers real-time visual alerts and generates "
                "a formatted electronic mail broadcast. The email contains executive incident metrics, affected SKUs, days overdue, and SOP directives "
                "(safe disposal vs FIFO markdown). This dispatch is logged to 'alerts.log' for compliance audit trails. If all items are SAFE, silent standard logs are written."
            ),
            "eg": "Example: An email broadcast is generated with subject '[CRITICAL EXPIRY ALERT] Immediate Action Required: 2 Expired / 3 Near Expiry'."
        },
        {
            "q": "Q8: What is FIFO (First-In, First-Out) and how does Node 7 implement Cycle Resolution?",
            "a": (
                "FIFO is the gold standard for perishable inventory: items that expire earliest must be sold or utilized first. "
                "Node 7 [UpdateOut -> CheckOut] provides an interactive checkout interface. When items are sold, damaged, or disposed, "
                "the user specifies the quantity removed. If quantity drops to zero, the record can be cleanly deleted or archived, refreshing the dashboard."
            ),
            "eg": "Example: A store sells 5 cartons of milk expiring in 4 days. Node 7 deducts 5 units from stock, leaving 7 units remaining."
        },
        {
            "q": "Q9: How did you design the Streamlit Web User Interface?",
            "a": (
                "The Streamlit app (app.py) is divided into 5 intuitive tabs:\n"
                " 1. Real-Time Dashboard: Visual KPI cards, alert banners, filterable tables, and inventory distribution charts.\n"
                " 2. Manual Entry Form: Date picker, category selector, and SKU generator.\n"
                " 3. AI / Image Scan: Drag-and-drop label image uploader with Gemini extraction and review modal.\n"
                " 4. Stock Checkout & Safe Disposal: Single item reduction and 1-click bulk hazardous disposal.\n"
                " 5. Audit Log Viewer: Live inspection and download of 'alerts.log'."
            ),
            "eg": "Example: Store managers can click '1-Click Safe Disposal' to purge all expired items in one operation."
        },
        {
            "q": "Q10: What automated testing did you implement to ensure code reliability?",
            "a": (
                "We built 21 automated unit and integration tests (test_expiry_tracker.py) covering:\n"
                " - Mathematical equation verification (past dates, today = 0, future dates).\n"
                " - Decision boundary checks (0d -> EXPIRED, 30d -> NEAR EXPIRY, 31d -> SAFE).\n"
                " - Database CRUD, UPSERT quantity increments, and bulk disposal.\n"
                " - Alert trigger logic and email payload generation.\n"
                " - OCR heuristic parsing and partial/full checkout flows."
            ),
            "eg": "Example: Running 'python -m unittest test_expiry_tracker.py' validates all 21 test cases in under 2 seconds."
        },
        {
            "q": "Q11: How do you protect secrets and sensitive credentials in this project?",
            "a": (
                "We follow the Twelve-Factor App methodology: all database passwords and Gemini API keys are loaded from environment variables "
                "via python-dotenv into frozen dataclasses in config.py. A .gitignore file strictly excludes .env, *.db, and *.log files from Git, "
                "while providing a clean .env.example template for new team members."
            ),
            "eg": "Example: GitHub Push Protection automatically prevented accidental secret leakage during repository push."
        },
        {
            "q": "Q12: If you were asked to scale this system for 500 supermarket stores, what would you add?",
            "a": (
                "For enterprise scale, I would introduce:\n"
                " 1. Distributed Tasks: Celery with Redis for asynchronous nightly expiry calculation jobs across millions of SKUs.\n"
                " 2. Connection Pooling: PgBouncer for handling thousands of concurrent PostgreSQL connections.\n"
                " 3. Cloud Object Storage: AWS S3 or Google Cloud Storage to store original label photos.\n"
                " 4. Live Email Relays: Amazon SES or SendGrid for actual transactional email delivery to floor managers.\n"
                " 5. Role-Based Access Control (RBAC): Differentiating Cashiers (checkout only) from Store Managers (disposal approval)."
            ),
            "eg": "Example: Nightly cron job runs at 12:01 AM across all 500 stores, automatically emailing regional managers by 6:00 AM."
        }
    ]

    for item in qa_list:
        # Question Header Box
        pdf.set_fill_color(240, 244, 250)
        pdf.set_draw_color(200, 215, 235)
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.set_text_color(25, 118, 210)
        pdf.cell(0, 7.5, f"  {item['q']}", border=1, fill=True, ln=True)

        # Answer Body
        pdf.ln(1.5)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 5, item["a"])
        pdf.ln(1)

        # Real-World Example Box
        pdf.set_fill_color(255, 250, 240)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(160, 90, 0)
        pdf.multi_cell(0, 4.8, f"   [REAL-WORLD EXAMPLE]: {item['eg']}", fill=True)
        pdf.ln(4)

    # --- SECTION 4: KEY TAKEAWAYS & CHEAT SHEET TABLE ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(25, 118, 210)
    pdf.cell(0, 8, "4. Quick Technical Cheat Sheet for Quick Revision", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    cheat_sheet_data = [
        ("Component", "Tech Stack", "Design Pattern / Core Responsibility"),
        ("Frontend UI", "Streamlit & Pandas", "Interactive KPI metrics, responsive tabs, visual charts"),
        ("CLI Engine", "Python 3.10+ / Rich", "Terminal state machine, ANSI tables, and status badges"),
        ("AI Vision", "Google GenAI (Gemini 3.5)", "Multimodal packaging OCR, date normalization to ISO-8601"),
        ("Database", "PostgreSQL (psycopg2)", "Raw SQL, parameterized UPSERT, SQLite automatic fallback"),
        ("Lifespan Core", "Custom Engine (Pydantic)", "Equation: Days = Expiry - Current; Boundary logic"),
        ("Alert Dispatch", "AlertManager (alerts.py)", "Real-time dashboard warnings, simulated email broadcast"),
        ("Testing Suite", "unittest (Python stdlib)", "21 unit/integration tests verifying all architecture nodes"),
        ("Config / Secrets", "python-dotenv", "12-Factor App methodology, .gitignore credentials security"),
    ]

    # Render table
    col_widths = [35, 45, 110]
    # Header
    pdf.set_fill_color(25, 118, 210)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9.5)
    for i, title in enumerate(cheat_sheet_data[0]):
        pdf.cell(col_widths[i], 7.5, title, border=1, fill=True, align="C" if i < 2 else "L")
    pdf.ln()

    # Rows
    pdf.set_font("Helvetica", "", 9)
    for row_idx, row in enumerate(cheat_sheet_data[1:]):
        fill = (row_idx % 2 == 1)
        pdf.set_fill_color(248, 250, 252) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(30, 30, 30)
        for i, val in enumerate(row):
            align = "C" if i < 2 else "L"
            bold_font = (i == 0)
            if bold_font:
                pdf.set_font("Helvetica", "B", 9)
            else:
                pdf.set_font("Helvetica", "", 9)
            pdf.cell(col_widths[i], 6.5, val, border=1, fill=fill, align=align)
        pdf.ln()

    pdf.ln(8)
    pdf.set_fill_color(232, 245, 233)
    pdf.set_draw_color(56, 142, 60)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(27, 94, 32)
    pdf.cell(0, 8, "  [PRO-TIP FOR INTERVIEWS]:", border=1, fill=True, ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 40, 40)
    pro_tip = (
        "When asked about this project in an interview, structure your answer using the STAR method:\n"
        "- Situation: Supermarkets lose massive revenue and face safety violations from expired products.\n"
        "- Task: Build an automated, resilient end-to-end tracking system with AI vision and raw SQL database.\n"
        "- Action: Designed a 7-node architecture with Google Gemini Vision, PostgreSQL UPSERT, and dynamic FIFO rules.\n"
        "- Result: Zero-click label extraction, 100% test coverage with 21 unit tests, and real-time email broadcast alerts."
    )
    pdf.multi_cell(0, 5, pro_tip, fill=True)

    # Output PDF
    pdf.output(str(pdf_path))
    print(f"SUCCESS: Interview Guide PDF generated at: {pdf_path}")


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    diagram_file = base_dir / "architecture_flow_diagram.png"
    pdf_file = base_dir / "Product_Expiry_Tracking_System_Interview_Preparation_Guide.pdf"

    print("Generating flow diagram image...")
    create_flow_diagram_image(diagram_file)

    print("Generating interview preparation guide PDF...")
    generate_pdf(pdf_file, diagram_file)
