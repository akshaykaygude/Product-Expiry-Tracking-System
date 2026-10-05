"""
==============================================================================
MODULE: inventory_service.py
DESCRIPTION: Business Orchestration Service for Inventory Operations.
==============================================================================

EDUCATIONAL ARCHITECTURE NOTES:
The Service Layer pattern decouples presentation/CLI layers from data persistence
and external AI models.
It coordinates:
1. Ingestion: Form parsing and validation into persistent PostgreSQL storage.
2. Lifespan Evaluation: Calling the computation core to produce statuses and metrics.
3. Checkout / Cycle Resolution: Reducing quantities, executing safe disposals,
   and completing inventory item lifecycles.
"""

from __future__ import annotations
from datetime import date, timedelta
from typing import List, Optional, Tuple

from alerts import alert_manager, EmailBroadcast
from database import db_manager
from lifespan_engine import lifespan_engine
from models import (
    ExpiryStatus,
    InventoryItem,
    InventorySummary,
    LifespanAnalysis,
)


class InventoryService:
    """
    Coordinates high-level business use cases for the inventory management lifecycle.
    """

    def __init__(self) -> None:
        self.db = db_manager
        self.engine = lifespan_engine
        self.alerts = alert_manager

    def register_item(
        self,
        sku: str,
        name: str,
        category: str,
        expiry_date: date,
        quantity: int = 1
    ) -> InventoryItem:
        """
        Validates, normalizes, and persists an inventory record into the database.
        """
        item = InventoryItem(
            sku=sku,
            name=name,
            category=category,
            expiry_date=expiry_date,
            quantity=quantity
        )
        saved_item = self.db.insert_or_upsert_item(item)
        return saved_item

    def get_evaluated_inventory(
        self,
        current_date: Optional[date] = None
    ) -> Tuple[List[LifespanAnalysis], InventorySummary, Optional[EmailBroadcast]]:
        """
        Executes Nodes 4, 5, and 6:
        1. Queries all records from DB.
        2. Computes lifespan equation (Days = Expiry - Current).
        3. Evaluates status boundaries (EXPIRED, NEAR EXPIRY, SAFE).
        4. Triggers alerts / email broadcasts if urgent items are present.
        """
        raw_items = self.db.get_all_items()
        analyses, summary = self.engine.analyze_inventory(raw_items, current_date=current_date)
        broadcast = self.alerts.evaluate_and_trigger(analyses, summary)
        return analyses, summary, broadcast

    def check_out_item(
        self,
        sku: str,
        quantity_to_remove: int,
        auto_delete_if_zero: bool = False
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Executes Node 7 [UpdateOut -> CheckOut]:
        Reduces on-hand inventory quantity when stock is sold, rotated, or disposed.
        Returns: (success: bool, message: str, remaining_quantity: Optional[int])
        """
        clean_sku = sku.strip().upper()
        existing = self.db.get_item_by_sku(clean_sku)

        if not existing:
            return False, f"Item with SKU '{clean_sku}' was not found in inventory.", None

        if quantity_to_remove <= 0:
            return False, "Quantity to check out must be a positive integer greater than 0.", existing.quantity

        if quantity_to_remove > existing.quantity:
            return (
                False,
                f"Checkout rejected: Requested {quantity_to_remove} units, but only {existing.quantity} units are in stock.",
                existing.quantity
            )

        new_quantity = existing.quantity - quantity_to_remove

        if new_quantity == 0 and auto_delete_if_zero:
            self.db.delete_item(clean_sku)
            return True, f"All stock ({quantity_to_remove} units) checked out. Record for '{clean_sku}' removed from database.", 0
        else:
            self.db.update_item_quantity(clean_sku, new_quantity)
            return True, f"Successfully checked out {quantity_to_remove} units. Remaining stock: {new_quantity} units.", new_quantity

    def bulk_dispose_expired(self, current_date: Optional[date] = None) -> int:
        """
        One-click hazardous disposal: Deletes all items that have reached EXPIRED status
        (Days Remaining <= 0).
        """
        ref_date = current_date or date.today()
        count = self.db.bulk_dispose_expired_items(ref_date)
        return count

    def delete_item(self, sku: str) -> bool:
        """
        Explicitly removes an item record from the database.
        """
        return self.db.delete_item(sku)

    def seed_demo_data(self, current_date: Optional[date] = None) -> int:
        """
        Populates the database with realistic sample items covering all three
        status boundaries (EXPIRED, NEAR EXPIRY, SAFE).
        """
        today = current_date or date.today()

        sample_items = [
            # 1. EXPIRED ITEMS (Days Remaining <= 0)
            InventoryItem(
                sku="SKU-MILK-PAST",
                name="FarmFresh Whole Milk 1L",
                category="Dairy",
                expiry_date=today - timedelta(days=5),
                quantity=4
            ),
            InventoryItem(
                sku="SKU-YOG-EXPD",
                name="Artisan Greek Yogurt 500g",
                category="Dairy",
                expiry_date=today - timedelta(days=1),
                quantity=8
            ),

            # 2. NEAR EXPIRY ITEMS (0 < Days Remaining <= 30 Days)
            InventoryItem(
                sku="SKU-BRD-NEAR",
                name="Sourdough Whole Wheat Bread",
                category="Bakery",
                expiry_date=today + timedelta(days=4),
                quantity=12
            ),
            InventoryItem(
                sku="SKU-CHK-NEAR",
                name="Free-Range Chicken Breast 500g",
                category="Meat",
                expiry_date=today + timedelta(days=9),
                quantity=6
            ),
            InventoryItem(
                sku="SKU-BER-NEAR",
                name="Organic Fresh Blueberries 250g",
                category="Produce",
                expiry_date=today + timedelta(days=18),
                quantity=15
            ),

            # 3. SAFE ITEMS (Days Remaining > 30 Days)
            InventoryItem(
                sku="SKU-TUNA-SAFE",
                name="Wild Skipjack Tuna in Olive Oil",
                category="Canned Goods",
                expiry_date=today + timedelta(days=180),
                quantity=45
            ),
            InventoryItem(
                sku="SKU-PST-SAFE",
                name="Bronze-Cut Penne Rigate 1kg",
                category="General",
                expiry_date=today + timedelta(days=365),
                quantity=30
            ),
            InventoryItem(
                sku="SKU-ASP-SAFE",
                name="Cardio Aspirin 100mg (100 Tabs)",
                category="Pharmaceuticals",
                expiry_date=today + timedelta(days=450),
                quantity=20
            ),
        ]

        seeded_count = 0
        for item in sample_items:
            self.db.insert_or_upsert_item(item)
            seeded_count += 1

        return seeded_count


# Global singleton instance
inventory_service = InventoryService()
