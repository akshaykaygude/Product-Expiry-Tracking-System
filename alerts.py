"""
==============================================================================
MODULE: alerts.py
DESCRIPTION: Real-Time Alert Triggers, Dashboard Warnings & Email Broadcasts.
==============================================================================

EDUCATIONAL ARCHITECTURE NOTES:
In accordance with Node 6 [AlertTrigger / Dash] of the architecture blueprint:
1. Alert Trigger Decision Logic:
   - If ANY item is classified as EXPIRED or NEAR EXPIRY:
     * Triggers real-time dashboard visual alerts (high-contrast banner).
     * Simulates an urgent email broadcast to inventory store managers.
     * Records incident audit logs in 'alerts.log'.
   - If ALL items are SAFE:
     * Suppresses urgent sirens and routes execution to standard Dash
       operational inventory logs.

2. Production Simulation:
   In cloud deployments, this service interfaces with Amazon SES, SendGrid,
   or SMTP relays. Here, it formats professional HTML and text payloads,
   dispatches to the alert logging subsystem, and generates human-readable
   broadcast telemetry for terminal dashboards.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from config import alert_config
from models import ExpiryStatus, InventorySummary, LifespanAnalysis


@dataclass
class EmailBroadcast:
    """
    Simulated electronic mail payload generated during urgent alert triggers.
    """
    sender: str
    recipient: str
    subject: str
    timestamp: datetime
    body_text: str
    is_urgent: bool
    affected_skus_count: int


class AlertManager:
    """
    Coordinates visual dashboard warnings, automated email broadcasts,
    and audit logging for inventory safety compliance.
    """

    def __init__(self) -> None:
        self.config = alert_config
        self.log_file_path: Path = self.config.log_file

    def evaluate_and_trigger(
        self,
        analyses: List[LifespanAnalysis],
        summary: InventorySummary
    ) -> Optional[EmailBroadcast]:
        """
        Main decision gate for Node 6:
        - If critical items exist -> Formats & triggers urgent email broadcast.
        - If safe -> Logs standard operational log.
        """
        if summary.has_critical_alerts:
            broadcast = self.generate_urgent_email_broadcast(analyses, summary)
            self._log_broadcast(broadcast)
            return broadcast
        else:
            self._log_standard_inventory_status(summary)
            return None

    def generate_urgent_email_broadcast(
        self,
        analyses: List[LifespanAnalysis],
        summary: InventorySummary
    ) -> EmailBroadcast:
        """
        Constructs an urgent notification broadcast for retail floor managers.
        """
        now = datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")

        critical_items = [
            a for a in analyses
            if a.status in (ExpiryStatus.EXPIRED, ExpiryStatus.NEAR_EXPIRY)
        ]

        subject = (
            f"[CRITICAL EXPIRY ALERT] Immediate Action Required: "
            f"{summary.expired_items_count} Expired / {summary.near_expiry_items_count} Near Expiry"
        )

        body_lines = [
            "=" * 78,
            "                   URGENT INVENTORY STATUS BROADCAST",
            "=" * 78,
            f"TIMESTAMP:    {timestamp_str}",
            f"FROM:         {self.config.sender_email}",
            f"TO:           {self.config.manager_email}",
            f"ALERT LEVEL:  CRITICAL (ACTION REQUIRED WITHIN 24 HOURS)",
            "-" * 78,
            "EXECUTIVE INCIDENT SUMMARY:",
            f"  * Expired SKUs:      {summary.expired_items_count} ({summary.expired_units_count} total units) -> MANDATORY DISPOSAL",
            f"  * Near Expiry SKUs:  {summary.near_expiry_items_count} ({summary.near_expiry_units_count} total units) -> ROTATION / FIFO",
            f"  * Safe SKUs:         {summary.safe_items_count} ({summary.safe_units_count} units)",
            "-" * 78,
            "ACTIONABLE INVENTORY BREAKDOWN:",
            f"{'SKU':<14} | {'ITEM NAME':<26} | {'EXPIRY':<10} | {'DAYS':<5} | {'STATUS':<12} | {'ACTION':<20}",
            "-" * 78,
        ]

        for a in critical_items:
            days_str = f"{a.days_remaining:+d}" if a.days_remaining <= 0 else f"{a.days_remaining}"
            name_truncated = (a.item.name[:24] + "..") if len(a.item.name) > 26 else a.item.name
            action_short = "DISPOSE SAFELY" if a.status == ExpiryStatus.EXPIRED else "FIFO ROTATION"
            body_lines.append(
                f"{a.item.sku:<14} | {name_truncated:<26} | {a.item.expiry_date.isoformat():<10} | {days_str:<5} | {a.status.value:<12} | {action_short:<20}"
            )

        body_lines.extend([
            "-" * 78,
            "STANDARD OPERATING INSTRUCTIONS:",
            "  1. EXPIRED STOCK: Pull from retail shelves immediately and log quarantine disposal.",
            "  2. NEAR EXPIRY STOCK: Apply promotional markdown tags and prioritize display per FIFO.",
            "=" * 78,
            "Broadcast dispatched automatically by Product Expiry Tracking System Core Engine.",
            "=" * 78,
        ])

        body_text = "\n".join(body_lines)

        return EmailBroadcast(
            sender=self.config.sender_email,
            recipient=self.config.manager_email,
            subject=subject,
            timestamp=now,
            body_text=body_text,
            is_urgent=True,
            affected_skus_count=len(critical_items)
        )

    def _log_broadcast(self, broadcast: EmailBroadcast) -> None:
        """
        Appends the transmitted broadcast into the persistent alert log.
        """
        log_entry = (
            f"\n--- [EMAIL BROADCAST DISPATCHED: {broadcast.timestamp.isoformat()}] ---\n"
            f"SENDER: {broadcast.sender}\n"
            f"RECIPIENT: {broadcast.recipient}\n"
            f"SUBJECT: {broadcast.subject}\n"
            f"PAYLOAD:\n{broadcast.body_text}\n"
            f"{'-' * 80}\n"
        )
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception:
            pass

    def _log_standard_inventory_status(self, summary: InventorySummary) -> None:
        """
        Logs routine clean inventory state when all stock is in SAFE status.
        """
        now = datetime.now()
        log_entry = (
            f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] [STANDARD LOG] "
            f"Inventory Scan Normal: All {summary.total_distinct_items} items "
            f"({summary.total_physical_units} units) are SAFE. No alerts triggered.\n"
        )
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception:
            pass


# Global singleton instance
alert_manager = AlertManager()
