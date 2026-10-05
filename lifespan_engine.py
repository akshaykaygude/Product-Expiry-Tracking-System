"""
==============================================================================
MODULE: lifespan_engine.py
DESCRIPTION: Lifespan Computation & Status Boundary Evaluation Core.
==============================================================================

EDUCATIONAL ARCHITECTURE NOTES:
In accordance with Node 5 [Calc -> StatusCheck] of the architecture blueprint:
1. Lifespan Equation:
   Days Remaining = Expiry Date - Current Date
   (Calculated strictly using calendar date delta).

2. Decision Tree Boundary Conditions:
   - EXPIRED:     Days Remaining <= 0
   - NEAR EXPIRY: 0 < Days Remaining <= Threshold (default 30 Days)
   - SAFE:        Days Remaining > Threshold (30 Days)

3. Separation of Concerns & Determinism:
   - The engine accepts an optional 'current_date' parameter. This makes the
     calculation 100% deterministic and testable across past, present,
     and future time horizons.
   - Enforces business actions (FIFO stock rotation vs. hazardous disposal)
     derived directly from the mathematical status.
"""

from __future__ import annotations
from datetime import date
from typing import List, Optional, Tuple

from config import lifespan_config
from models import (
    ExpiryStatus,
    InventoryItem,
    InventorySummary,
    LifespanAnalysis,
    RecommendedAction,
)


class LifespanEngine:
    """
    Core computational engine for calculating lifespan and assigning
    status classifications to inventory items.
    """

    def __init__(self, threshold_days: Optional[int] = None) -> None:
        self.threshold_days: int = threshold_days if threshold_days is not None else lifespan_config.threshold_days

    def calculate_days_remaining(self, expiry_date: date, current_date: Optional[date] = None) -> int:
        """
        Computes the fundamental lifespan equation:
        Days Remaining = Expiry Date - Current Date
        """
        ref_date = current_date if current_date is not None else date.today()
        delta = expiry_date - ref_date
        return delta.days

    def evaluate_status(self, days_remaining: int, threshold_days: Optional[int] = None) -> ExpiryStatus:
        """
        Evaluates the status boundary for a given days_remaining value:
          - Days Remaining <= 0          -> EXPIRED
          - 0 < Days Remaining <= Thresh -> NEAR EXPIRY
          - Days Remaining > Thresh      -> SAFE
        """
        thresh = threshold_days if threshold_days is not None else self.threshold_days

        if days_remaining <= 0:
            return ExpiryStatus.EXPIRED
        elif days_remaining <= thresh:
            return ExpiryStatus.NEAR_EXPIRY
        else:
            return ExpiryStatus.SAFE

    def get_recommended_action(self, status: ExpiryStatus) -> str:
        """
        Assigns standard operational guidance based on the evaluation status.
        """
        if status == ExpiryStatus.EXPIRED:
            return RecommendedAction.DISPOSAL.value
        elif status == ExpiryStatus.NEAR_EXPIRY:
            return RecommendedAction.ROTATION.value
        else:
            return RecommendedAction.STANDARD.value

    def analyze_item(self, item: InventoryItem, current_date: Optional[date] = None) -> LifespanAnalysis:
        """
        Executes complete lifecycle evaluation on a single InventoryItem:
        1. Computes days remaining.
        2. Assigns status boundary.
        3. Identifies operational action.
        4. Flags urgent alert necessity.
        """
        days_rem = self.calculate_days_remaining(item.expiry_date, current_date=current_date)
        status = self.evaluate_status(days_rem)
        action = self.get_recommended_action(status)
        is_urgent = (status in (ExpiryStatus.EXPIRED, ExpiryStatus.NEAR_EXPIRY))

        return LifespanAnalysis(
            item=item,
            days_remaining=days_rem,
            status=status,
            recommended_action=action,
            is_urgent=is_urgent,
        )

    def analyze_inventory(
        self,
        items: List[InventoryItem],
        current_date: Optional[date] = None
    ) -> Tuple[List[LifespanAnalysis], InventorySummary]:
        """
        Batches analysis over a collection of items, producing:
        1. A sorted list of analyzed items (Prioritized: Expired first, then Near Expiry, then Safe).
        2. An executive InventorySummary with aggregate operational metrics.
        """
        analyses: List[LifespanAnalysis] = []
        summary = InventorySummary()

        for item in items:
            analysis = self.analyze_item(item, current_date=current_date)
            analyses.append(analysis)

            # Update aggregate statistics
            summary.total_distinct_items += 1
            summary.total_physical_units += item.quantity

            if analysis.status == ExpiryStatus.EXPIRED:
                summary.expired_items_count += 1
                summary.expired_units_count += item.quantity
            elif analysis.status == ExpiryStatus.NEAR_EXPIRY:
                summary.near_expiry_items_count += 1
                summary.near_expiry_units_count += item.quantity
            else:
                summary.safe_items_count += 1
                summary.safe_units_count += item.quantity

        # Sorting logic:
        # Most critical first (Days remaining ascending: most negative days first)
        analyses.sort(key=lambda a: (0 if a.status == ExpiryStatus.EXPIRED else (1 if a.status == ExpiryStatus.NEAR_EXPIRY else 2), a.days_remaining))

        return analyses, summary


# Global singleton instance
lifespan_engine = LifespanEngine()
