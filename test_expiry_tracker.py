"""
==============================================================================
MODULE: test_expiry_tracker.py
DESCRIPTION: Comprehensive Unit and Integration Test Suite.
==============================================================================

EDUCATIONAL ARCHITECTURE NOTES:
Production-ready test engineering mandates:
1. Complete deterministic unit tests isolating the Lifespan Engine equations.
2. Integration tests validating raw SQL persistence (CRUD + UPSERT).
3. Boundary value analysis on 0-day, threshold-day, and negative-day horizons.
4. Alerting verification ensuring simulated email broadcasts trigger only on
   EXPIRED and NEAR EXPIRY items.
"""

import unittest
from datetime import date, timedelta
from pathlib import Path

from alerts import AlertManager, alert_manager
from config import LifespanConfig
from database import DatabaseManager
from gemini_extractor import GeminiExtractor
from inventory_service import InventoryService
from lifespan_engine import LifespanEngine
from models import (
    ExpiryStatus,
    InventoryItem,
    RecommendedAction,
)


class TestLifespanEngine(unittest.TestCase):
    """
    Validates Node 5 [Calc -> StatusCheck] mathematical equations and boundaries.
    """

    def setUp(self) -> None:
        self.engine = LifespanEngine(threshold_days=30)
        self.today = date(2026, 10, 5)

    def test_lifespan_equation_positive(self) -> None:
        """Verify: Days Remaining = Expiry Date - Current Date (> 0)"""
        expiry = date(2026, 10, 15)
        days = self.engine.calculate_days_remaining(expiry, current_date=self.today)
        self.assertEqual(days, 10)

    def test_lifespan_equation_zero(self) -> None:
        """Verify: Expiry Date == Current Date yields 0 Days Remaining."""
        expiry = self.today
        days = self.engine.calculate_days_remaining(expiry, current_date=self.today)
        self.assertEqual(days, 0)

    def test_lifespan_equation_negative(self) -> None:
        """Verify: Past Expiry Date yields negative Days Remaining."""
        expiry = date(2026, 10, 1)
        days = self.engine.calculate_days_remaining(expiry, current_date=self.today)
        self.assertEqual(days, -4)

    def test_boundary_expired_negative(self) -> None:
        """Boundary: Days Remaining < 0 -> EXPIRED"""
        status = self.engine.evaluate_status(-3)
        self.assertEqual(status, ExpiryStatus.EXPIRED)

    def test_boundary_expired_zero(self) -> None:
        """Boundary: Days Remaining == 0 -> EXPIRED"""
        status = self.engine.evaluate_status(0)
        self.assertEqual(status, ExpiryStatus.EXPIRED)

    def test_boundary_near_expiry_lower(self) -> None:
        """Boundary: Days Remaining == 1 -> NEAR EXPIRY"""
        status = self.engine.evaluate_status(1)
        self.assertEqual(status, ExpiryStatus.NEAR_EXPIRY)

    def test_boundary_near_expiry_upper(self) -> None:
        """Boundary: Days Remaining == 30 (Threshold) -> NEAR EXPIRY"""
        status = self.engine.evaluate_status(30)
        self.assertEqual(status, ExpiryStatus.NEAR_EXPIRY)

    def test_boundary_safe(self) -> None:
        """Boundary: Days Remaining == 31 (> Threshold) -> SAFE"""
        status = self.engine.evaluate_status(31)
        self.assertEqual(status, ExpiryStatus.SAFE)

    def test_recommended_action_mapping(self) -> None:
        """Verify actions: EXPIRED -> Disposal, NEAR -> Rotation, SAFE -> Standard"""
        self.assertEqual(self.engine.get_recommended_action(ExpiryStatus.EXPIRED), RecommendedAction.DISPOSAL.value)
        self.assertEqual(self.engine.get_recommended_action(ExpiryStatus.NEAR_EXPIRY), RecommendedAction.ROTATION.value)
        self.assertEqual(self.engine.get_recommended_action(ExpiryStatus.SAFE), RecommendedAction.STANDARD.value)

    def test_inventory_batch_analysis_sorting(self) -> None:
        """Verify sorting order: EXPIRED items appear first, sorted by days ascending."""
        items = [
            InventoryItem(sku="SKU-SAFE", name="Safe Item", expiry_date=self.today + timedelta(days=60), quantity=1),
            InventoryItem(sku="SKU-EXP-1", name="Expired Item 1", expiry_date=self.today - timedelta(days=5), quantity=1),
            InventoryItem(sku="SKU-NEAR", name="Near Item", expiry_date=self.today + timedelta(days=10), quantity=1),
            InventoryItem(sku="SKU-EXP-2", name="Expired Item 2", expiry_date=self.today - timedelta(days=15), quantity=1),
        ]
        analyses, summary = self.engine.analyze_inventory(items, current_date=self.today)

        self.assertEqual(summary.expired_items_count, 2)
        self.assertEqual(summary.near_expiry_items_count, 1)
        self.assertEqual(summary.safe_items_count, 1)
        self.assertTrue(summary.has_critical_alerts)

        # Most expired first (-15 days, then -5 days)
        self.assertEqual(analyses[0].item.sku, "SKU-EXP-2")
        self.assertEqual(analyses[1].item.sku, "SKU-EXP-1")
        self.assertEqual(analyses[2].item.sku, "SKU-NEAR")
        self.assertEqual(analyses[3].item.sku, "SKU-SAFE")


class TestDatabaseOperations(unittest.TestCase):
    """
    Validates Node 4 [DB] parameterized SQL queries and persistence.
    """

    def setUp(self) -> None:
        self.db = DatabaseManager()
        self.db.clear_all()

    def tearDown(self) -> None:
        self.db.clear_all()

    def test_insert_and_fetch_item(self) -> None:
        """Verify inserting an item and fetching it by SKU."""
        item = InventoryItem(
            sku="SKU-TEST-001",
            name="Organic Greek Yogurt",
            category="Dairy",
            expiry_date=date(2026, 11, 15),
            quantity=10
        )
        saved = self.db.insert_or_upsert_item(item)
        self.assertEqual(saved.sku, "SKU-TEST-001")

        fetched = self.db.get_item_by_sku("sku-test-001") # Case-insensitive lookup
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Organic Greek Yogurt")
        self.assertEqual(fetched.quantity, 10)

    def test_upsert_increments_quantity(self) -> None:
        """Verify that inserting duplicate SKU updates quantity additively."""
        item1 = InventoryItem(
            sku="SKU-DUP-01",
            name="Almond Milk",
            category="Beverages",
            expiry_date=date(2026, 11, 20),
            quantity=5
        )
        self.db.insert_or_upsert_item(item1)

        item2 = InventoryItem(
            sku="SKU-DUP-01",
            name="Almond Milk",
            category="Beverages",
            expiry_date=date(2026, 11, 25),
            quantity=3
        )
        updated = self.db.insert_or_upsert_item(item2)
        self.assertEqual(updated.quantity, 8)
        self.assertEqual(updated.expiry_date, date(2026, 11, 25))

    def test_update_quantity(self) -> None:
        """Verify altering inventory quantity."""
        item = InventoryItem(
            sku="SKU-QTY-01",
            name="White Bread",
            category="Bakery",
            expiry_date=date(2026, 10, 12),
            quantity=20
        )
        self.db.insert_or_upsert_item(item)
        success = self.db.update_item_quantity("SKU-QTY-01", 14)
        self.assertTrue(success)

        fetched = self.db.get_item_by_sku("SKU-QTY-01")
        self.assertEqual(fetched.quantity, 14)

    def test_delete_item(self) -> None:
        """Verify deleting an item by SKU."""
        item = InventoryItem(
            sku="SKU-DEL-01",
            name="Salmon Fillet",
            category="Meat",
            expiry_date=date(2026, 10, 8),
            quantity=2
        )
        self.db.insert_or_upsert_item(item)
        deleted = self.db.delete_item("SKU-DEL-01")
        self.assertTrue(deleted)
        self.assertIsNone(self.db.get_item_by_sku("SKU-DEL-01"))

    def test_bulk_dispose_expired(self) -> None:
        """Verify bulk deletion of records prior to or on cutoff date."""
        today = date(2026, 10, 5)
        self.db.insert_or_upsert_item(InventoryItem(sku="SKU-EXP-A", name="Old Item A", expiry_date=today - timedelta(days=2), quantity=1))
        self.db.insert_or_upsert_item(InventoryItem(sku="SKU-EXP-B", name="Old Item B", expiry_date=today, quantity=2))
        self.db.insert_or_upsert_item(InventoryItem(sku="SKU-FUT-C", name="Future Item C", expiry_date=today + timedelta(days=10), quantity=5))

        removed_count = self.db.bulk_dispose_expired_items(today)
        self.assertEqual(removed_count, 2)

        remaining = self.db.get_all_items()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].sku, "SKU-FUT-C")


class TestAlertAndNotificationTriggers(unittest.TestCase):
    """
    Validates Node 6 [AlertTrigger / Dash] alerting rules and broadcast formatting.
    """

    def setUp(self) -> None:
        self.manager = AlertManager()
        self.engine = LifespanEngine()
        self.today = date(2026, 10, 5)

    def test_alert_fires_when_expired_or_near_expiry_present(self) -> None:
        """Verify alert triggers an EmailBroadcast when critical stock is detected."""
        items = [
            InventoryItem(sku="SKU-URGENT", name="Expiring Yogurt", expiry_date=self.today + timedelta(days=2), quantity=4),
            InventoryItem(sku="SKU-SAFE", name="Dry Pasta", expiry_date=self.today + timedelta(days=90), quantity=10),
        ]
        analyses, summary = self.engine.analyze_inventory(items, current_date=self.today)
        broadcast = self.manager.evaluate_and_trigger(analyses, summary)

        self.assertIsNotNone(broadcast)
        self.assertTrue(broadcast.is_urgent)
        self.assertIn("CRITICAL EXPIRY ALERT", broadcast.subject)
        self.assertIn("SKU-URGENT", broadcast.body_text)

    def test_alert_suppressed_when_all_items_safe(self) -> None:
        """Verify no email alert is dispatched when all stock is safely > 30 days."""
        items = [
            InventoryItem(sku="SKU-SAFE-1", name="Canned Corn", expiry_date=self.today + timedelta(days=120), quantity=5),
            InventoryItem(sku="SKU-SAFE-2", name="Olive Oil", expiry_date=self.today + timedelta(days=200), quantity=2),
        ]
        analyses, summary = self.engine.analyze_inventory(items, current_date=self.today)
        broadcast = self.manager.evaluate_and_trigger(analyses, summary)

        self.assertIsNone(broadcast)


class TestAIExtractionAndOCR(unittest.TestCase):
    """
    Validates Node 3 [AI/Image Scan -> OCR -> Gemini] parsing and schema normalization.
    """

    def setUp(self) -> None:
        self.extractor = GeminiExtractor()

    def test_heuristic_parser_extracts_all_attributes(self) -> None:
        """Verify extracting SKU, Name, Expiry Date, and Quantity from OCR stream."""
        raw_ocr = (
            "ARTISAN BLUEBERRY MUFFIN 4-PACK\n"
            "LOT# MUF-3341\n"
            "BEST BEFORE: 2026-10-19\n"
            "QTY: 8 PACKS"
        )
        result = self.extractor.extract_from_text(raw_ocr)

        self.assertEqual(result.sku, "MUF-3341")
        self.assertEqual(result.expiry_date, date(2026, 10, 19))
        self.assertEqual(result.quantity, 8)
        self.assertEqual(result.category, "Bakery")
        self.assertIn("MUFFIN", result.name.upper())


class TestCheckoutResolution(unittest.TestCase):
    """
    Validates Node 7 [UpdateOut -> CheckOut -> End] stock deduction and disposal.
    """

    def setUp(self) -> None:
        self.service = InventoryService()
        self.service.db.clear_all()
        self.today = date(2026, 10, 5)

    def tearDown(self) -> None:
        self.service.db.clear_all()

    def test_partial_checkout(self) -> None:
        """Verify deducting partial quantity keeps record with updated count."""
        self.service.register_item(
            sku="SKU-CHCK-01",
            name="Cheddar Cheese 200g",
            category="Dairy",
            expiry_date=self.today + timedelta(days=20),
            quantity=15
        )
        success, msg, remaining = self.service.check_out_item("SKU-CHCK-01", quantity_to_remove=5)
        self.assertTrue(success)
        self.assertEqual(remaining, 10)

        item = self.service.db.get_item_by_sku("SKU-CHCK-01")
        self.assertEqual(item.quantity, 10)

    def test_checkout_exceeding_stock_rejected(self) -> None:
        """Verify attempting to check out more than in stock fails safely."""
        self.service.register_item(
            sku="SKU-CHCK-02",
            name="Organic Butter",
            category="Dairy",
            expiry_date=self.today + timedelta(days=15),
            quantity=3
        )
        success, msg, remaining = self.service.check_out_item("SKU-CHCK-02", quantity_to_remove=10)
        self.assertFalse(success)
        self.assertEqual(remaining, 3)

    def test_checkout_to_zero_with_auto_delete(self) -> None:
        """Verify checking out all stock with auto_delete removes record."""
        self.service.register_item(
            sku="SKU-CHCK-03",
            name="Fresh Orange Juice",
            category="Beverages",
            expiry_date=self.today + timedelta(days=5),
            quantity=4
        )
        success, msg, remaining = self.service.check_out_item("SKU-CHCK-03", quantity_to_remove=4, auto_delete_if_zero=True)
        self.assertTrue(success)
        self.assertEqual(remaining, 0)
        self.assertIsNone(self.service.db.get_item_by_sku("SKU-CHCK-03"))


if __name__ == "__main__":
    unittest.main()
