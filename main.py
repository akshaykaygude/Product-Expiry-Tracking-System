"""
==============================================================================
MODULE: main.py
DESCRIPTION: Production-Ready Entry Point & Lifecycle Orchestrator.
==============================================================================

EDUCATIONAL ARCHITECTURE NOTES:
This is the master orchestration module executing the exact Mermaid workflow:

       Start([User Logs In / Opens System]) --> Mode{Input Method}
       Mode -->|Manual Entry| Form[Fill Item Details: SKU, Name, Expiry Date]
       Mode -->|AI / Image Scan| OCR[Upload Photo of Label / Barcode]
       OCR --> Gemini[AI / OCR Extracts Expiry Date]
       Gemini --> Form
       Form --> DB[(PostgreSQL / Database Update)]
       DB --> Calc[Compute: Days Remaining = Expiry Date - Current Date]
       Calc --> StatusCheck{Evaluate Days Remaining}
       StatusCheck -->|Days <= 0| Expired[Mark Status: EXPIRED]
       StatusCheck -->|0 < Days <= Threshold| Near[Mark Status: NEAR EXPIRY]
       StatusCheck -->|Days > Threshold| Safe[Mark Status: SAFE]
       Expired --> AlertTrigger[Trigger Real-Time Dashboard & Email Alerts]
       Near --> AlertTrigger
       Safe --> Dash[Display standard inventory lists & reports]
       AlertTrigger --> Action[Action: Stock Rotation / FIFO / Safe Disposal]
       Dash --> UpdateOut{Is Stock Disposed/Sold?}
       Action --> UpdateOut
       UpdateOut -->|Yes| CheckOut[Check-out / Reduce Inventory Quantity]
       UpdateOut -->|No| Calc
       CheckOut --> End([End Logic Session])

Every node in this state machine is fully implemented with zero placeholders.
"""

from __future__ import annotations
import argparse
from pathlib import Path
import sys
from datetime import date
from typing import Optional

from rich.console import Console
from rich.prompt import Confirm, Prompt

from inventory_service import inventory_service
from models import ExpiryStatus
from ui import (
    capture_ai_scan_form,
    capture_manual_entry_form,
    console,
    prompt_checkout_resolution,
    render_banner,
    render_dashboard,
    render_diagnostics,
    render_email_broadcast_modal,
    render_main_menu,
)


def run_pipeline_cycle(auto_prompt_checkout: bool = True) -> None:
    """
    Executes the downstream processing pipeline from DB through Calc, StatusCheck,
    AlertTrigger, Action, and UpdateOut.
    """
    # Node 4 -> Node 5: Fetch from DB and execute Calc -> StatusCheck
    analyses, summary, broadcast = inventory_service.get_evaluated_inventory()

    # Node 6: Action Triggers / Dashboard visual reporting
    render_dashboard(analyses, summary, broadcast)

    if broadcast is not None:
        view_email = Confirm.ask("\n[bold red]Would you like to inspect the dispatched email alert broadcast?[/bold red]", default=True)
        if view_email:
            render_email_broadcast_modal(broadcast)

    # Node 7: Cycle Resolution [UpdateOut -> CheckOut -> End]
    if auto_prompt_checkout and summary.total_distinct_items > 0:
        console.print("\n" + "-" * 80)
        is_stock_out = Confirm.ask(
            "[bold yellow]UpdateOut Decision: Has any stock been sold, rotated, or disposed?[/bold yellow]",
            default=False
        )

        if is_stock_out:
            raw_items = inventory_service.db.get_all_items()
            resolution = prompt_checkout_resolution(raw_items)
            if resolution:
                sku, qty_to_remove, delete_if_zero = resolution
                success, msg, remaining = inventory_service.check_out_item(
                    sku=sku,
                    quantity_to_remove=qty_to_remove,
                    auto_delete_if_zero=delete_if_zero
                )
                if success:
                    console.print(f"[bold green]✓ {msg}[/bold green]")
                    # Loop back to Calc to refresh state per diagram (UpdateOut --> No --> Calc)
                    console.print("[dim]Refreshing inventory status...[/dim]")
                    refreshed_analyses, refreshed_summary, refreshed_broadcast = inventory_service.get_evaluated_inventory()
                    render_dashboard(refreshed_analyses, refreshed_summary, refreshed_broadcast)
                else:
                    console.print(f"[bold red]✗ {msg}[/bold red]")


def handle_manual_entry_branch() -> None:
    """
    Branch 1: [Manual Entry -> Form -> DB -> Calc]
    """
    item = capture_manual_entry_form()
    if item:
        saved = inventory_service.save_item(item)
        console.print(f"\n[bold green]✓ Record securely committed to database (SKU: {saved.sku})[/bold green]")
        # Flow automatically progresses to Calc -> StatusCheck -> ActionTriggers
        run_pipeline_cycle(auto_prompt_checkout=True)


def handle_ai_scan_branch() -> None:
    """
    Branch 2: [AI / Image Scan -> OCR -> Gemini -> Form -> DB -> Calc]
    """
    item = capture_ai_scan_form()
    if item:
        saved = inventory_service.save_item(item)
        console.print(f"\n[bold green]✓ AI-extracted record saved to database (SKU: {saved.sku})[/bold green]")
        # Flow automatically progresses to Calc -> StatusCheck -> ActionTriggers
        run_pipeline_cycle(auto_prompt_checkout=True)


def handle_checkout_branch() -> None:
    """
    Direct resolution branch: [UpdateOut -> CheckOut -> End]
    """
    raw_items = inventory_service.db.get_all_items()
    if not raw_items:
        console.print("[yellow]No items in database to check out.[/yellow]")
        return

    resolution = prompt_checkout_resolution(raw_items)
    if resolution:
        sku, qty_to_remove, delete_if_zero = resolution
        success, msg, remaining = inventory_service.check_out_item(
            sku=sku,
            quantity_to_remove=qty_to_remove,
            auto_delete_if_zero=delete_if_zero
        )
        if success:
            console.print(f"[bold green]✓ {msg}[/bold green]")
            run_pipeline_cycle(auto_prompt_checkout=False)
        else:
            console.print(f"[bold red]✗ {msg}[/bold red]")


def handle_seed_demo_branch() -> None:
    """
    Populates sample data illustrating EXPIRED, NEAR EXPIRY, and SAFE states.
    """
    count = inventory_service.seed_demo_data()
    console.print(f"\n[bold green]✓ Seeded {count} realistic demonstration items into database.[/bold green]")
    run_pipeline_cycle(auto_prompt_checkout=True)


def main_loop() -> None:
    """
    Node 1 [Start -> Mode]:
    Main operational event loop connecting all architectural nodes.
    """
    while True:
        console.clear()
        render_banner()
        choice = render_main_menu()

        if choice == "1":
            handle_manual_entry_branch()
        elif choice == "2":
            handle_ai_scan_branch()
        elif choice == "3":
            run_pipeline_cycle(auto_prompt_checkout=True)
        elif choice == "4":
            handle_checkout_branch()
        elif choice == "5":
            handle_seed_demo_branch()
        elif choice == "6":
            render_diagnostics()
        elif choice == "0":
            console.print("\n[bold cyan]Closing logic session. Goodbye![/bold cyan]")
            break

        # Pause before clearing screen for next iteration
        if choice != "0":
            Prompt.ask("\n[dim]Press Enter to continue...[/dim]", default="")


def parse_cli_args() -> argparse.Namespace:
    """
    Command-line interface argument parser for automated and headless executions.
    """
    parser = argparse.ArgumentParser(
        description="Product Expiry Tracking System (FMCG / Retail FIFO Engine)"
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed sample inventory items (Expired, Near Expiry, Safe) and display dashboard."
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Display the real-time inventory dashboard non-interactively and exit."
    )
    parser.add_argument(
        "--test-ai",
        type=str,
        metavar="TEXT_OR_IMAGE",
        help="Test Gemini AI extraction on a given image file or raw text string."
    )
    parser.add_argument(
        "--clear-db",
        action="store_true",
        help="Purge all inventory records from the database."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_cli_args()

    # Handle non-interactive CLI flags
    if args.clear_db:
        inventory_service.db.clear_all()
        console.print("[bold green]✓ Database inventory table truncated successfully.[/bold green]")
        sys.exit(0)

    if args.seed:
        render_banner()
        count = inventory_service.seed_demo_data()
        console.print(f"[bold green]✓ Seeded {count} demo records.[/bold green]")
        analyses, summary, broadcast = inventory_service.get_evaluated_inventory()
        render_dashboard(analyses, summary, broadcast)
        sys.exit(0)

    if args.dashboard:
        render_banner()
        analyses, summary, broadcast = inventory_service.get_evaluated_inventory()
        render_dashboard(analyses, summary, broadcast)
        sys.exit(0)

    if args.test_ai:
        render_banner()
        console.print(f"[bold cyan]Testing AI Extraction on input: {args.test_ai}[/bold cyan]")
        p = Path(args.test_ai)
        from gemini_extractor import gemini_extractor
        if p.exists() and p.is_file():
            if p.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
                result = gemini_extractor.extract_from_image(p)
            else:
                result = gemini_extractor.extract_from_text(p.read_text(encoding="utf-8"))
        else:
            result = gemini_extractor.extract_from_text(args.test_ai)
        console.print(result)
        sys.exit(0)

    # Launch interactive state machine
    try:
        main_loop()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Session interrupted. Exiting gracefully.[/yellow]")
        sys.exit(0)
