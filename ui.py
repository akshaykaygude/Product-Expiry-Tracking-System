"""
==============================================================================
MODULE: ui.py
DESCRIPTION: Terminal User Interface & Rich Reporting Presentation Layer.
==============================================================================

EDUCATIONAL ARCHITECTURE NOTES:
This module represents the View/Presentation layer in the architectural pipeline.
It leverages the 'rich' library to construct an intuitive, interactive CLI
with:
1. High-contrast status badges (Expired=Red, Near-Expiry=Yellow, Safe=Green).
2. Actionable FIFO recommendation badges.
3. Form validation loops for manual input and AI-extracted data reviews.
4. Simulated urgent email dispatch banners matching Node 6 [AlertTrigger].
"""

from __future__ import annotations
import sys
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Tuple

from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

from alerts import EmailBroadcast
from config import alert_config, db_config, gemini_config, lifespan_config
from database import db_manager
from gemini_extractor import gemini_extractor
from models import (
    AIExtractionResult,
    ExpiryStatus,
    InventoryItem,
    InventorySummary,
    LifespanAnalysis,
)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(legacy_windows=False)


def render_banner() -> None:
    """
    Renders stylized system header with operational engine diagnostics.
    """
    title_text = Text()
    title_text.append("[PRODUCT EXPIRY TRACKING SYSTEM]\n", style="bold cyan")
    title_text.append("Production-Grade FMCG / Retail Lifespan & FIFO Management\n", style="dim white")

    db_status = db_manager.get_status_info()
    engine_name = db_status.get("engine", "PostgreSQL")
    fallback_note = " (Local Fallback)" if db_status.get("is_fallback") else " (Connected)"
    ai_status = f"{gemini_config.model_name} (Live API)" if gemini_extractor.is_live() else "Local Heuristic OCR (Gemini Fallback)"

    info_text = (
        f"[bold white]Database:[/bold white] [green]{engine_name}{fallback_note}[/green]  |  "
        f"[bold white]AI Vision:[/bold white] [magenta]{ai_status}[/magenta]  |  "
        f"[bold white]Near Expiry Threshold:[/bold white] [yellow]{lifespan_config.threshold_days} Days[/yellow]"
    )

    console.print(
        Panel(
            Align.center(f"{title_text}\n{info_text}"),
            box=box.ROUNDED,
            border_style="bright_blue",
            padding=(0, 2)
        )
    )


def render_main_menu() -> str:
    """
    Renders Node 1 [Start -> Mode] input selection menu.
    """
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Key", style="bold cyan", width=6)
    table.add_column("Workflow Action", style="white")

    table.add_row("[1]", "Input Branch 1: Manual Data Entry (SKU, Name, Expiry Date)")
    table.add_row("[2]", "Input Branch 2: AI / Image Scan (Gemini Vision OCR)")
    table.add_row("[3]", "Processing Core & Action Triggers: View Inventory Dashboard & Lifespan Status")
    table.add_row("[4]", "Cycle Resolution: Check-Out / Stock Reduction / Disposal")
    table.add_row("[5]", "Demo Seed: Populate Sample Data (Expired, Near Expiry, Safe)")
    table.add_row("[6]", "Diagnostics: View PostgreSQL & Gemini System Health")
    table.add_row("[0]", "End Logic Session / Exit Application")

    console.print(
        Panel(table, title="[bold white]MAIN OPERATIONAL WORKFLOW[/bold white]", border_style="cyan")
    )

    choice = Prompt.ask(
        "[bold cyan]Select workflow branch[/bold cyan]",
        choices=["1", "2", "3", "4", "5", "6", "0"],
        default="3"
    )
    return choice


def capture_manual_entry_form() -> Optional[InventoryItem]:
    """
    Node 2 [Manual Entry -> Form]:
    Captures item attributes with strict type checking and validation.
    """
    console.print("\n[bold cyan]=== [FORM] MANUAL INVENTORY ENTRY ===[/bold cyan]")
    console.print("[dim]Enter product attributes. All fields are strictly validated.[/dim]\n")

    # 1. SKU
    while True:
        sku = Prompt.ask("[bold white]SKU Code[/bold white] (e.g., 'SKU-MILK-101', or press Enter to auto-generate)").strip()
        if not sku:
            timestamp_slug = datetime.now().strftime("%m%d%H%M%S")[-5:]
            sku = f"SKU-ITM-{timestamp_slug}"
            console.print(f"  [dim green]↳ Generated SKU: {sku}[/dim green]")
            break
        if len(sku) >= 2:
            sku = sku.upper()
            break
        console.print("[bold red]SKU must be at least 2 characters.[/bold red]")

    # 2. Product Name
    while True:
        name = Prompt.ask("[bold white]Product Name[/bold white] (e.g., 'Organic Whole Milk 1L')").strip()
        if name:
            break
        console.print("[bold red]Product Name cannot be blank.[/bold red]")

    # 3. Category
    categories = ["Dairy", "Bakery", "Meat", "Produce", "Beverages", "Canned Goods", "Pharmaceuticals", "General"]
    category = Prompt.ask(
        "[bold white]Category[/bold white]",
        choices=categories,
        default="General"
    )

    # 4. Expiry Date
    while True:
        exp_input = Prompt.ask(
            "[bold white]Expiration Date[/bold white] (Format: YYYY-MM-DD)",
            default=(date.today().replace(month=date.today().month % 12 + 1) if date.today().month < 12 else date.today()).isoformat()
        ).strip()
        try:
            exp_date = date.fromisoformat(exp_input)
            break
        except ValueError:
            console.print("[bold red]Invalid date format. Please specify strictly as YYYY-MM-DD (e.g. 2026-11-30).[/bold red]")

    # 5. Quantity
    qty = IntPrompt.ask("[bold white]Initial Quantity in Stock[/bold white]", default=1)
    if qty < 0:
        qty = 0

    # Summary confirmation
    review_table = Table(box=box.ROUNDED, show_header=False)
    review_table.add_column("Field", style="bold yellow")
    review_table.add_column("Value", style="bold white")
    review_table.add_row("SKU", sku)
    review_table.add_row("Item Name", name)
    review_table.add_row("Category", category)
    review_table.add_row("Expiry Date", exp_date.isoformat())
    review_table.add_row("Quantity", str(qty))

    console.print("\n[bold white]Review Entered Form Data:[/bold white]")
    console.print(review_table)

    confirm = Confirm.ask("Commit and inject record into database?", default=True)
    if not confirm:
        console.print("[yellow]Entry cancelled by user.[/yellow]")
        return None

    return InventoryItem(
        sku=sku,
        name=name,
        category=category,
        expiry_date=exp_date,
        quantity=qty
    )


def capture_ai_scan_form() -> Optional[InventoryItem]:
    """
    Node 3 [AI/Image Scan -> OCR -> Gemini]:
    Ingests image file or raw text OCR stream, passes to Gemini,
    and displays extracted attributes in an editable form for confirmation.
    """
    console.print("\n[bold magenta]=== [AI/OCR] MULTIMODAL GEMINI EXTRACTION ===[/bold magenta]")
    console.print("[dim]Select ingestion mode to extract SKU, Item Name, and Expiry Date.[/dim]\n")

    console.print("  [1] Scan from Image File (JPG, PNG, WEBP)")
    console.print("  [2] Paste Raw Scanned Text / OCR String")
    console.print("  [3] Test with Built-In Sample FMCG Label")

    mode = Prompt.ask("[bold magenta]Select scan mode[/bold magenta]", choices=["1", "2", "3"], default="3")

    extraction_result: AIExtractionResult

    if mode == "1":
        path_str = Prompt.ask("[bold white]Enter absolute or relative image file path[/bold white]").strip()
        path = Path(path_str)
        if not path.exists():
            console.print(f"[bold red]File not found at: {path}[/bold red]")
            return None
        with console.status("[bold magenta]Analyzing image with Google Gemini Vision...[/bold magenta]"):
            extraction_result = gemini_extractor.extract_from_image(path)

    elif mode == "2":
        console.print("[bold white]Paste OCR / Barcode label text (press Enter when done):[/bold white]")
        raw_text = Prompt.ask("OCR Stream")
        with console.status("[bold magenta]Parsing OCR text with Gemini Engine...[/bold magenta]"):
            extraction_result = gemini_extractor.extract_from_text(raw_text)

    else:
        sample_label = (
            "SUNNYVALE ARTISAN BRIE CHEESE 250G\n"
            "BARCODE / LOT: SKU-BRIE-772\n"
            "BEST BEFORE DATE: 2026-10-28\n"
            "PACK QTY: 8 UNITS"
        )
        console.print("\n[bold white]Sample Label Stream Ingested:[/bold white]")
        console.print(Panel(sample_label, border_style="dim magenta"))
        with console.status("[bold magenta]Parsing sample label with Gemini Engine...[/bold magenta]"):
            extraction_result = gemini_extractor.extract_from_text(sample_label)

    # Display Extracted Attributes
    console.print("\n[bold green][SUCCESS] AI Extraction Complete![/bold green]")
    extract_table = Table(box=box.ROUNDED)
    extract_table.add_column("Attribute", style="bold cyan")
    extract_table.add_column("Extracted Value", style="bold white")
    extract_table.add_column("Confidence & Source", style="dim white")

    extract_table.add_row("SKU", extraction_result.sku or "Auto-Generated", "Gemini OCR")
    extract_table.add_row("Product Name", extraction_result.name, "Gemini Vision")
    extract_table.add_row("Category", extraction_result.category or "General", "AI Classification")
    extract_table.add_row("Expiry Date", extraction_result.expiry_date.isoformat(), "ISO-8601 Normalized")
    extract_table.add_row("Quantity", str(extraction_result.quantity), "Extracted Units")

    console.print(extract_table)
    if extraction_result.confidence_notes:
        console.print(f"[dim]Note: {extraction_result.confidence_notes}[/dim]\n")

    # Allow user to edit or accept the form
    edit_choice = Confirm.ask("Do you wish to modify any of the extracted fields before saving?", default=False)
    final_sku = extraction_result.sku or f"SKU-{datetime.now().strftime('%m%d%H%M')}"
    final_name = extraction_result.name
    final_category = extraction_result.category or "General"
    final_exp = extraction_result.expiry_date
    final_qty = extraction_result.quantity

    if edit_choice:
        final_sku = Prompt.ask("SKU", default=final_sku).strip().upper()
        final_name = Prompt.ask("Product Name", default=final_name).strip()
        final_category = Prompt.ask("Category", default=final_category).strip()
        while True:
            exp_str = Prompt.ask("Expiry Date (YYYY-MM-DD)", default=final_exp.isoformat()).strip()
            try:
                final_exp = date.fromisoformat(exp_str)
                break
            except ValueError:
                console.print("[red]Invalid date format. Use YYYY-MM-DD.[/red]")
        final_qty = IntPrompt.ask("Quantity", default=final_qty)

    confirm_save = Confirm.ask("Inject verified record into Database?", default=True)
    if not confirm_save:
        console.print("[yellow]AI scan entry aborted.[/yellow]")
        return None

    return InventoryItem(
        sku=final_sku,
        name=final_name,
        category=final_category,
        expiry_date=final_exp,
        quantity=final_qty
    )


def render_dashboard(
    analyses: List[LifespanAnalysis],
    summary: InventorySummary,
    broadcast: Optional[EmailBroadcast]
) -> None:
    """
    Nodes 5 & 6 [Calc -> StatusCheck -> AlertTrigger / Dash]:
    Renders visual inventory KPI cards, high-contrast alerts, and table reports.
    """
    console.print("\n" + "=" * 80)
    console.print(Align.center("[bold cyan][DASHBOARD] PRODUCT EXPIRY TRACKING SYSTEM — REAL-TIME STATUS[/bold cyan]"))
    console.print("=" * 80 + "\n")

    # 1. KPI Summary Cards
    kpi_table = Table(box=box.ROUNDED, show_header=True, expand=True)
    kpi_table.add_column("Total SKUs", justify="center", style="bold white")
    kpi_table.add_column("Total Units", justify="center", style="bold white")
    kpi_table.add_column("EXPIRED (<=0d)", justify="center", style="bold red")
    kpi_table.add_column("NEAR EXPIRY (<=30d)", justify="center", style="bold yellow")
    kpi_table.add_column("SAFE (>30d)", justify="center", style="bold green")

    kpi_table.add_row(
        str(summary.total_distinct_items),
        str(summary.total_physical_units),
        f"{summary.expired_items_count} items ({summary.expired_units_count} units)",
        f"{summary.near_expiry_items_count} items ({summary.near_expiry_units_count} units)",
        f"{summary.safe_items_count} items ({summary.safe_units_count} units)",
    )
    console.print(kpi_table)

    # 2. Alert Trigger Layer (Node 6)
    if broadcast is not None:
        alert_text = (
            f"[bold red][!] REAL-TIME ALERT TRIGGERED: IMMEDIATE ACTION REQUIRED [!][/bold red]\n"
            f"[white]{summary.expired_items_count} items are EXPIRED (hazardous disposal mandatory) and "
            f"{summary.near_expiry_items_count} items are NEAR EXPIRY (FIFO stock rotation required).[/white]\n"
            f"[dim green]>> Urgent email broadcast simulated and dispatched to {broadcast.recipient}[/dim green]"
        )
        console.print(Panel(alert_text, border_style="bold red", padding=(1, 2)))
    elif summary.total_distinct_items > 0:
        clean_text = "[bold green][OK] STANDARD DASHBOARD LOG: All inventory items are SAFE. No alerts triggered.[/bold green]"
        console.print(Panel(clean_text, border_style="green", padding=(0, 2)))

    # 3. Detailed Inventory Table
    if not analyses:
        console.print("\n[yellow]No inventory items currently registered in the database.[/yellow]")
        return

    table = Table(box=box.HEAVY_EDGE, expand=True)
    table.add_column("SKU", style="bold white", width=16)
    table.add_column("Product Name", style="white", min_width=22)
    table.add_column("Category", style="cyan", width=14)
    table.add_column("Expiry Date", justify="center", width=12)
    table.add_column("Days Left", justify="right", width=10)
    table.add_column("Status", justify="center", width=15)
    table.add_column("Qty", justify="right", width=6)
    table.add_column("Recommended Action (FIFO / Safety)", style="italic", width=34)

    for a in analyses:
        # Status Badge Styling
        if a.status == ExpiryStatus.EXPIRED:
            status_badge = "[bold white on red] EXPIRED [/bold white on red]"
            days_style = "bold red"
            action_style = "bold red"
        elif a.status == ExpiryStatus.NEAR_EXPIRY:
            status_badge = "[bold black on yellow] NEAR EXPIRY [/bold black on yellow]"
            days_style = "bold yellow"
            action_style = "bold yellow"
        else:
            status_badge = "[bold white on green] SAFE [/bold white on green]"
            days_style = "green"
            action_style = "dim white"

        days_text = f"[{days_style}]{a.days_remaining:+d} d[/{days_style}]" if a.days_remaining <= 0 else f"[{days_style}]{a.days_remaining} d[/{days_style}]"

        table.add_row(
            a.item.sku,
            a.item.name,
            a.item.category,
            a.item.expiry_date.isoformat(),
            days_text,
            status_badge,
            str(a.item.quantity),
            f"[{action_style}]{a.recommended_action}[/{action_style}]"
        )

    console.print("\n[bold white]Inventory Register Breakdown (Sorted by FIFO Urgency):[/bold white]")
    console.print(table)


def render_email_broadcast_modal(broadcast: EmailBroadcast) -> None:
    """
    Renders simulated electronic mail transmission banner.
    """
    header = (
        f"[bold white]FROM:[/bold white] {broadcast.sender}\n"
        f"[bold white]TO:[/bold white]   {broadcast.recipient}\n"
        f"[bold white]DATE:[/bold white] {broadcast.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"[bold white]SUBJ:[/bold white] [bold red]{broadcast.subject}[/bold red]\n"
    )
    console.print(
        Panel(
            f"{header}\n{broadcast.body_text}",
            title="[bold red][EMAIL BROADCAST] SIMULATED DISPATCH MODAL[/bold red]",
            border_style="red"
        )
    )


def prompt_checkout_resolution(items: List[InventoryItem]) -> Optional[Tuple[str, int, bool]]:
    """
    Node 7 [UpdateOut -> CheckOut -> End]:
    Facilitates item quantity alteration or complete removal upon sale/disposal.
    Returns: (sku, quantity_to_remove, auto_delete_if_zero) or None
    """
    console.print("\n[bold yellow]=== [CYCLE RESOLUTION] STOCK ROTATION & CHECK-OUT ===[/bold yellow]")
    console.print("[dim]Select an item to reduce quantity (sale) or remove (safe disposal / write-off).[/dim]\n")

    if not items:
        console.print("[yellow]Inventory is currently empty. Nothing to check out.[/yellow]")
        return None

    # Display selection index table
    selection_table = Table(box=box.SIMPLE, show_header=True)
    selection_table.add_column("#", style="bold cyan", width=4)
    selection_table.add_column("SKU", style="bold white", width=18)
    selection_table.add_column("Product Name", style="white")
    selection_table.add_column("Expiry Date", width=12)
    selection_table.add_column("In Stock", justify="right", width=10)

    for idx, item in enumerate(items, 1):
        selection_table.add_row(
            str(idx),
            item.sku,
            item.name,
            item.expiry_date.isoformat(),
            str(item.quantity)
        )
    console.print(selection_table)

    target_sku: str
    target_item: Optional[InventoryItem] = None

    while True:
        raw_choice = Prompt.ask("[bold cyan]Enter item # or exact SKU code (or 'C' to cancel)[/bold cyan]").strip()
        if raw_choice.upper() == 'C':
            return None

        # Try matching by index number
        if raw_choice.isdigit():
            idx_num = int(raw_choice)
            if 1 <= idx_num <= len(items):
                target_item = items[idx_num - 1]
                target_sku = target_item.sku
                break

        # Try matching by SKU
        matched = [i for i in items if i.sku.upper() == raw_choice.upper()]
        if matched:
            target_item = matched[0]
            target_sku = target_item.sku
            break

        console.print("[bold red]Invalid selection. Please enter a valid row number or SKU.[/bold red]")

    console.print(f"\nSelected: [bold white]{target_item.name}[/bold white] (SKU: {target_sku}, Stock: {target_item.quantity})")

    # Query units to check out
    while True:
        qty_to_remove = IntPrompt.ask(
            f"Enter quantity to check out / dispose (1 to {target_item.quantity})",
            default=target_item.quantity
        )
        if 1 <= qty_to_remove <= target_item.quantity:
            break
        console.print(f"[bold red]Quantity must be between 1 and {target_item.quantity}.[/bold red]")

    delete_if_zero = False
    if qty_to_remove == target_item.quantity:
        delete_if_zero = Confirm.ask(
            "This will reduce stock to 0. Remove this item record completely from database?",
            default=True
        )

    return target_sku, qty_to_remove, delete_if_zero


def render_diagnostics() -> None:
    """
    Renders diagnostic system information.
    """
    console.print("\n" + "=" * 80)
    console.print(Align.center("[bold cyan]🔧 SYSTEM ARCHITECTURE & DIAGNOSTICS[/bold cyan]"))
    console.print("=" * 80 + "\n")

    diag_table = Table(box=box.ROUNDED, show_header=True)
    diag_table.add_column("Component", style="bold white", width=24)
    diag_table.add_column("Status / Configured Value", style="bold green")

    # Database
    db_info = db_manager.get_status_info()
    diag_table.add_row("Database Engine", db_info.get("engine", "PostgreSQL"))
    if not db_info.get("is_fallback"):
        diag_table.add_row("Database Host:Port", f"{db_info.get('host')}:{db_info.get('port')}")
        diag_table.add_row("Database Name", db_info.get("database"))
        diag_table.add_row("Database User", db_info.get("user"))
    else:
        diag_table.add_row("SQLite File", db_info.get("file"))

    # Gemini
    ai_status = "Connected (Live API)" if gemini_extractor.is_live() else "Offline / Local Heuristic (Set GEMINI_API_KEY)"
    diag_table.add_row("Google GenAI Model", gemini_config.model_name)
    diag_table.add_row("Gemini API Key", "Configured (Masked)" if gemini_config.is_configured else "Unset (Using Fallback)")
    diag_table.add_row("AI Engine Status", ai_status)

    # Lifespan
    diag_table.add_row("Near Expiry Threshold", f"{lifespan_config.threshold_days} Days")
    diag_table.add_row("Alert Sender Email", alert_config.sender_email)
    diag_table.add_row("Manager Alert Email", alert_config.manager_email)
    diag_table.add_row("Alerts Log File", str(alert_config.log_file))

    console.print(diag_table)
    Prompt.ask("\n[dim]Press Enter to return to main menu...[/dim]", default="")
