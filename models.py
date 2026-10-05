"""
==============================================================================
MODULE: models.py
DESCRIPTION: Data models, validation schemas, and domain entities.
==============================================================================

EDUCATIONAL ARCHITECTURE NOTES:
Using strict Pydantic schemas provides:
1. Runtime Data Integrity: Any malformed dates, negative quantities, or invalid
   types fail immediately at the system boundary before hitting the database.
2. Self-Documenting API: Domain entities clearly express the schema contract.
3. Clean Type Hinting: Enables IDE autocompletion and static analysis.
"""

from __future__ import annotations
from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ExpiryStatus(str, Enum):
    """
    Standardized status values matching the Mermaid architectural decision nodes:
      - EXPIRED:     Days Remaining <= 0
      - NEAR EXPIRY: 0 < Days Remaining <= Threshold (30 Days)
      - SAFE:        Days Remaining > Threshold
    """
    EXPIRED = "EXPIRED"
    NEAR_EXPIRY = "NEAR EXPIRY"
    SAFE = "SAFE"


class RecommendedAction(str, Enum):
    """
    Standard operating procedures for inventory according to FIFO principles.
    """
    DISPOSAL = "Safe Disposal Required / Immediate Quarantine / Write-off"
    ROTATION = "Stock Rotation Required / Apply FIFO / Mark Down Discount"
    STANDARD = "Standard Shelf Placement / Routine Quality Check"


class InventoryItem(BaseModel):
    """
    Domain entity representing a single stock keeping unit (SKU) record.
    """
    id: Optional[int] = Field(default=None, description="Database auto-increment primary key")
    sku: str = Field(..., min_length=2, max_length=64, description="Unique Stock Keeping Unit code")
    name: str = Field(..., min_length=1, max_length=255, description="Full descriptive name of the item")
    category: str = Field(default="General", max_length=100, description="Product category classification")
    expiry_date: date = Field(..., description="Calendar expiration date (YYYY-MM-DD)")
    quantity: int = Field(default=1, ge=0, description="Physical units in stock (must be non-negative)")
    created_at: Optional[datetime] = Field(default=None, description="Timestamp of record creation")
    updated_at: Optional[datetime] = Field(default=None, description="Timestamp of last update")

    @field_validator("sku")
    @classmethod
    def clean_sku(cls, v: str) -> str:
        """Strip whitespace and enforce uppercase consistency for SKU codes."""
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("SKU cannot be empty or purely whitespace.")
        return cleaned

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        """Strip unnecessary surrounding whitespace from item name."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Item Name cannot be empty.")
        return cleaned


class LifespanAnalysis(BaseModel):
    """
    Output model of the Processing Core [Calc -> StatusCheck].
    Encapsulates the mathematical equation result, categorical boundary,
    and business action trigger recommendations.
    """
    item: InventoryItem
    days_remaining: int = Field(..., description="Calculated difference: Expiry Date - Current Date")
    status: ExpiryStatus = Field(..., description="Categorical status boundary classification")
    recommended_action: str = Field(..., description="Actionable inventory mitigation step")
    is_urgent: bool = Field(..., description="Flag signaling if dashboard and email alerts must fire")


class InventorySummary(BaseModel):
    """
    Aggregated operational metrics for executive reporting and alert broadcasts.
    """
    total_distinct_items: int = 0
    total_physical_units: int = 0
    expired_items_count: int = 0
    expired_units_count: int = 0
    near_expiry_items_count: int = 0
    near_expiry_units_count: int = 0
    safe_items_count: int = 0
    safe_units_count: int = 0

    @property
    def has_critical_alerts(self) -> bool:
        """Returns True if any expired or near-expiry inventory requires manager intervention."""
        return (self.expired_items_count > 0) or (self.near_expiry_items_count > 0)


class AIExtractionResult(BaseModel):
    """
    Schema parsed from Gemini API free-tier response.
    Maps scanned label OCR content into structured attributes ready for the form.
    """
    sku: Optional[str] = Field(default=None, description="Extracted barcode/SKU or auto-synthesized key")
    name: str = Field(..., description="Identified product name")
    category: Optional[str] = Field(default="General", description="Inferred product category")
    expiry_date: date = Field(..., description="Normalized expiration date (YYYY-MM-DD)")
    quantity: int = Field(default=1, ge=1, description="Quantity detected or default 1")
    confidence_notes: Optional[str] = Field(default=None, description="Extraction reasoning from Gemini")
    raw_text: Optional[str] = Field(default=None, description="Raw OCR / text snippet")
