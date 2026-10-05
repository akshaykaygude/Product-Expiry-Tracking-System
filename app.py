"""
==============================================================================
MODULE: app.py
DESCRIPTION: Streamlit User-Friendly Web Application & Interactive Dashboard.
==============================================================================

EDUCATIONAL ARCHITECTURE NOTES:
This application delivers a production-grade Web User Interface built on Streamlit,
faithfully mapping the entire Mermaid architectural workflow:

  [Start] -> [Input Method]
      ├── [Manual Entry -> Form -> DB]
      └── [AI / Image Scan -> Gemini Vision -> Form -> DB]
  --> [Calc: Days = Expiry - Today]
  --> [StatusCheck: Expired <= 0 | Near Expiry <= 30 | Safe > 30]
  --> [AlertTrigger & Dashboard Reporting]
  --> [UpdateOut / CheckOut Cycle Resolution]

Tech Stack:
  - Python 3.10+
  - PostgreSQL via psycopg2-binary (with local SQLite developer fallback)
  - Google Gemini API (Free tier via google-genai SDK)
  - Streamlit & Pandas for interactive analytics
"""

from __future__ import annotations
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

# Internal architectural modules
from alerts import alert_manager
from config import alert_config, db_config, gemini_config, lifespan_config
from database import db_manager
from gemini_extractor import gemini_extractor
from inventory_service import inventory_service
from lifespan_engine import lifespan_engine
from models import ExpiryStatus, InventoryItem

# ==============================================================================
# 1. STREAMLIT PAGE CONFIGURATION & STYLING
# ==============================================================================
st.set_page_config(
    page_title="Product Expiry Tracking System",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished, professional typography and card styling
st.markdown("""
<style>
    /* Metric card styles */
    .metric-container {
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
        color: white;
    }
    .metric-expired { background: linear-gradient(135deg, #d32f2f, #b71c1c); }
    .metric-near { background: linear-gradient(135deg, #f57c00, #e65100); }
    .metric-safe { background: linear-gradient(135deg, #388e3c, #1b5e20); }
    .metric-total { background: linear-gradient(135deg, #1976d2, #0d47a1); }
    
    .stAlert {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# 2. SIDEBAR: SYSTEM HEALTH, DIAGNOSTICS & SEEDING CONTROLS
# ==============================================================================
with st.sidebar:
    st.title("📦 Product Expiry Tracking System")
    st.caption("FMCG / Retail FIFO & Lifespan Management")
    st.markdown("---")

    # Engine Status Indicators
    st.subheader("System Infrastructure")
    db_info = db_manager.get_status_info()
    if not db_info.get("is_fallback"):
        st.success(f"**Database:** {db_info.get('engine')} ({db_info.get('host')}:{db_info.get('port')})")
    else:
        st.info(f"**Database:** {db_info.get('engine')}")

    ai_status = f"{gemini_config.model_name} (Live API)" if gemini_extractor.is_live() else "Local Heuristic OCR (Gemini Fallback)"
    if gemini_extractor.is_live():
        st.success(f"**AI Vision:** {ai_status}")
    else:
        st.warning(f"**AI Vision:** {ai_status}")

    st.write(f"**Near Expiry Threshold:** `{lifespan_config.threshold_days} Days`")
    st.write(f"**System Date:** `{date.today().isoformat()}`")

    st.markdown("---")
    st.subheader("⚡ Quick Controls")

    # 1-Click Demo Data Population
    if st.button("🌱 Seed Sample Demo Data", use_container_width=True, help="Populate 8 realistic items covering Expired, Near Expiry, and Safe states."):
        count = inventory_service.seed_demo_data()
        st.toast(f"Successfully seeded {count} demo records!", icon="✅")
        st.rerun()

    # Clear Database
    if st.button("🗑️ Purge All Inventory", use_container_width=True, help="Remove all items from the database."):
        inventory_service.db.clear_all()
        st.toast("Database inventory cleared.", icon="🧹")
        st.rerun()

    st.markdown("---")
    st.caption("Architecture: Python 3.10+ • PostgreSQL • Google GenAI • Streamlit")


# ==============================================================================
# 3. CORE LOGIC EVALUATION
# ==============================================================================
# Fetch all items and evaluate with the lifespan engine
analyses, summary, broadcast = inventory_service.get_evaluated_inventory()


# ==============================================================================
# 4. TABBED USER INTERFACE
# ==============================================================================
tabs = st.tabs([
    "📊 Real-Time Dashboard",
    "✍️ Manual Entry (Branch 1)",
    "📸 AI / Image Scan (Branch 2)",
    "🔄 Stock Checkout & Disposal (Node 7)",
    "📧 Email Alert Audit Log"
])


# ------------------------------------------------------------------------------
# TAB 1: REAL-TIME DASHBOARD & LIFESPAN MONITORING
# ------------------------------------------------------------------------------
with tabs[0]:
    st.header("📊 Product Expiry Tracking System — Real-Time Dashboard")
    st.caption("Lifespan Equation: Days Remaining = Expiry Date - Current Date")

    # KPI Top Metric Cards
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    with kpi_col1:
        st.metric(
            label="Total Inventory",
            value=f"{summary.total_distinct_items} SKUs",
            delta=f"{summary.total_physical_units} Units"
        )
    with kpi_col2:
        st.metric(
            label="🚨 EXPIRED (<=0 Days)",
            value=f"{summary.expired_items_count} SKUs",
            delta=f"{summary.expired_units_count} Units",
            delta_color="inverse"
        )
    with kpi_col3:
        st.metric(
            label="⚠️ NEAR EXPIRY (<=30 Days)",
            value=f"{summary.near_expiry_items_count} SKUs",
            delta=f"{summary.near_expiry_units_count} Units",
            delta_color="inverse"
        )
    with kpi_col4:
        st.metric(
            label="✅ SAFE (>30 Days)",
            value=f"{summary.safe_items_count} SKUs",
            delta=f"{summary.safe_units_count} Units"
        )

    st.markdown("---")

    # Action Trigger Notification Banner (Node 6)
    if broadcast is not None:
        st.error(
            f"🚨 **CRITICAL ALERT TRIGGERED:** {summary.expired_items_count} item(s) are **EXPIRED** "
            f"(immediate disposal mandatory) and {summary.near_expiry_items_count} item(s) are **NEAR EXPIRY** "
            f"(apply FIFO rotation discount)."
        )
        with st.expander("📧 View Dispatched Urgent Email Broadcast Payload", expanded=False):
            st.markdown(f"**From:** `{broadcast.sender}`  |  **To:** `{broadcast.recipient}`  |  **Time:** `{broadcast.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}`")
            st.markdown(f"**Subject:** `{broadcast.subject}`")
            st.code(broadcast.body_text, language="text")
    elif summary.total_distinct_items > 0:
        st.success("✅ **Standard Inventory Scan:** All items are currently within safe lifespan parameters. No alerts triggered.")

    # Search & Filter Controls
    filter_col1, filter_col2, filter_col3 = st.columns([2, 1, 1])
    with filter_col1:
        search_query = st.text_input("🔍 Search by SKU or Item Name", placeholder="e.g. Milk, YOG, Cheese...")
    with filter_col2:
        status_filter = st.selectbox("Filter by Status", ["All", "EXPIRED", "NEAR EXPIRY", "SAFE"])
    with filter_col3:
        categories = ["All"] + sorted(list({a.item.category for a in analyses})) if analyses else ["All"]
        category_filter = st.selectbox("Filter by Category", categories)

    # Filter analyses dataset
    filtered_analyses = analyses
    if search_query:
        q = search_query.strip().lower()
        filtered_analyses = [a for a in filtered_analyses if q in a.item.name.lower() or q in a.item.sku.lower()]
    if status_filter != "All":
        filtered_analyses = [a for a in filtered_analyses if a.status.value == status_filter]
    if category_filter != "All":
        filtered_analyses = [a for a in filtered_analyses if a.item.category == category_filter]

    # Render Inventory Table
    if filtered_analyses:
        table_rows = []
        for a in filtered_analyses:
            table_rows.append({
                "SKU": a.item.sku,
                "Product Name": a.item.name,
                "Category": a.item.category,
                "Expiry Date": a.item.expiry_date.isoformat(),
                "Days Remaining": a.days_remaining,
                "Status": a.status.value,
                "Quantity": a.item.quantity,
                "Recommended FIFO / Safety Action": a.recommended_action
            })

        df = pd.DataFrame(table_rows)

        # Style configuration for Pandas table
        def highlight_status(row):
            status = row["Status"]
            if status == "EXPIRED":
                return ["background-color: rgba(211, 47, 47, 0.2); font-weight: bold;"] * len(row)
            elif status == "NEAR EXPIRY":
                return ["background-color: rgba(245, 124, 0, 0.2);"] * len(row)
            else:
                return ["background-color: rgba(56, 142, 60, 0.1);"] * len(row)

        st.dataframe(
            df.style.apply(highlight_status, axis=1),
            use_container_width=True,
            hide_index=True
        )

        # Visual Analytics Charts
        st.markdown("### 📈 Visual Inventory Distribution")
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            status_counts = pd.DataFrame({
                "Status": ["EXPIRED", "NEAR EXPIRY", "SAFE"],
                "Count": [summary.expired_items_count, summary.near_expiry_items_count, summary.safe_items_count]
            })
            st.bar_chart(status_counts.set_index("Status"), color="#1976d2")
        with chart_col2:
            cat_counts = df["Category"].value_counts().reset_index()
            cat_counts.columns = ["Category", "Units"]
            st.bar_chart(cat_counts.set_index("Category"), color="#f57c00")

    else:
        st.info("No items match the current filter or inventory is empty. Click 'Seed Sample Demo Data' in the sidebar to populate items.")


# ------------------------------------------------------------------------------
# TAB 2: MANUAL ENTRY FORM (BRANCH 1)
# ------------------------------------------------------------------------------
with tabs[1]:
    st.header("✍️ Input Branch 1: Manual Item Registration")
    st.caption("Directly capture SKU, descriptive name, calendar expiry date, and unit count.")

    with st.form("manual_entry_form", clear_on_submit=True):
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            m_sku = st.text_input("SKU Code (or leave blank to auto-generate)", placeholder="e.g. SKU-MILK-101")
            m_name = st.text_input("Product Name *", placeholder="e.g. FarmFresh Whole Milk 1L")
            m_category = st.selectbox("Category", [
                "Dairy", "Bakery", "Meat", "Produce", "Beverages", "Canned Goods", "Pharmaceuticals", "General"
            ])
        with col_m2:
            default_exp = date.today() + timedelta(days=15)
            m_expiry = st.date_input("Expiration Date *", value=default_exp)
            m_quantity = st.number_input("Stock Quantity *", min_value=1, max_value=10000, value=10, step=1)

        submitted = st.form_submit_button("💾 Save Item into Database", use_container_width=True)

        if submitted:
            if not m_name.strip():
                st.error("Product Name is required.")
            else:
                final_sku = m_sku.strip().upper() if m_sku.strip() else f"SKU-ITM-{datetime.now().strftime('%m%d%H%M%S')[-5:]}"
                try:
                    saved = inventory_service.register_item(
                        sku=final_sku,
                        name=m_name.strip(),
                        category=m_category,
                        expiry_date=m_expiry,
                        quantity=int(m_quantity)
                    )
                    st.success(f"Item `{saved.name}` (SKU: `{saved.sku}`) committed to database!")
                    st.toast("Item registered successfully!", icon="✅")
                    st.rerun()
                except Exception as err:
                    st.error(f"Failed to persist item: {err}")


# ------------------------------------------------------------------------------
# TAB 3: AI & IMAGE SCAN (BRANCH 2 - GEMINI VISION)
# ------------------------------------------------------------------------------
with tabs[2]:
    st.header("📸 Input Branch 2: Multimodal Gemini AI Vision & OCR")
    st.caption("Upload packaging photos or paste OCR label streams to extract metadata automatically via Google Gemini.")

    scan_mode = st.radio("Choose Ingestion Source", ["🖼️ Upload Image File", "📝 Paste OCR Text", "🧪 Use Pre-Built Sample Labels"], horizontal=True)

    extracted_data: Optional[dict] = None

    if scan_mode == "🖼️ Upload Image File":
        uploaded_file = st.file_uploader("Upload Product Label Image", type=["png", "jpg", "jpeg", "webp"])
        if uploaded_file is not None:
            st.image(uploaded_file, caption="Uploaded Label Preview", width=360)
            if st.button("🔍 Extract with Gemini AI Vision", use_container_width=True):
                with st.spinner("Analyzing packaging with Gemini Vision..."):
                    img_bytes = uploaded_file.getvalue()
                    mime_type = uploaded_file.type or "image/jpeg"
                    res = gemini_extractor.extract_from_image(img_bytes, mime_type=mime_type)
                    extracted_data = res.model_dump()

    elif scan_mode == "📝 Paste OCR Text":
        ocr_input = st.text_area("Paste Scanned Barcode / OCR Label Text", height=130, placeholder="DAIRY FARM GREEK YOGURT 500G\nLOT# YOG-9921\nUSE BY: 2026-10-18\nQTY: 12 PACKS")
        if st.button("🔍 Extract from OCR Text", use_container_width=True):
            if ocr_input.strip():
                with st.spinner("Parsing OCR text with Gemini Engine..."):
                    res = gemini_extractor.extract_from_text(ocr_input)
                    extracted_data = res.model_dump()
            else:
                st.warning("Please paste some OCR text to analyze.")

    else:
        sample_options = {
            "Milk Label (Dairy)": "sample_labels/sample_ocr_milk.txt",
            "Pharmacy Amoxicillin (Pharmaceuticals)": "sample_labels/sample_ocr_pharmacy.txt",
            "Artisan Cheese Label (Image)": "sample_labels/artisan_cheese_label.png"
        }
        chosen_sample = st.selectbox("Select Sample Asset", list(sample_options.keys()))
        sample_path = Path(sample_options[chosen_sample])

        if sample_path.exists():
            if sample_path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                st.image(str(sample_path), caption=chosen_sample, width=420)
            else:
                st.code(sample_path.read_text(encoding="utf-8"), language="text")

            if st.button("🚀 Analyze Sample Asset with Gemini", use_container_width=True):
                with st.spinner("Processing sample asset..."):
                    if sample_path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                        res = gemini_extractor.extract_from_image(sample_path)
                    else:
                        res = gemini_extractor.extract_from_text(sample_path.read_text(encoding="utf-8"))
                    extracted_data = res.model_dump()

    # If attributes were extracted, show review & confirmation form
    if extracted_data or "last_extracted" in st.session_state:
        if extracted_data:
            st.session_state["last_extracted"] = extracted_data
        cur_ext = st.session_state["last_extracted"]

        st.markdown("---")
        st.subheader("📋 Verified AI Extraction Form")
        st.caption("Review extracted attributes. You may adjust any field before committing to database.")

        with st.form("ai_review_form"):
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                ai_sku = st.text_input("Extracted SKU", value=cur_ext.get("sku") or "")
                ai_name = st.text_input("Product Name", value=cur_ext.get("name") or "")
                ai_cat = st.text_input("Category", value=cur_ext.get("category") or "General")
            with col_a2:
                ai_exp_val = cur_ext.get("expiry_date")
                if isinstance(ai_exp_val, str):
                    ai_exp_val = date.fromisoformat(ai_exp_val)
                ai_exp = st.date_input("Expiration Date", value=ai_exp_val or date.today())
                ai_qty = st.number_input("Quantity", min_value=1, value=int(cur_ext.get("quantity", 1)), step=1)

            st.caption(f"Confidence Note: {cur_ext.get('confidence_notes')}")
            confirm_ai_save = st.form_submit_button("✅ Commit Verified Record to Database", use_container_width=True)

            if confirm_ai_save:
                saved = inventory_service.register_item(
                    sku=ai_sku.strip().upper(),
                    name=ai_name.strip(),
                    category=ai_cat.strip(),
                    expiry_date=ai_exp,
                    quantity=int(ai_qty)
                )
                st.session_state.pop("last_extracted", None)
                st.toast(f"Successfully saved {saved.name} (SKU: {saved.sku})", icon="🎉")
                st.rerun()


# ------------------------------------------------------------------------------
# TAB 4: STOCK CHECKOUT & DISPOSAL (NODE 7)
# ------------------------------------------------------------------------------
with tabs[3]:
    st.header("🔄 Cycle Resolution: Stock Checkout & Safe Disposal")
    st.caption("Node 7 [UpdateOut -> CheckOut -> End]: Record sales, inventory rotation, or hazardous waste disposal.")

    col_res1, col_res2 = st.columns(2)

    with col_res1:
        st.subheader("📦 Single Item Checkout (Sales / Usage)")
        all_db_items = inventory_service.db.get_all_items()
        if all_db_items:
            item_display_map = {f"{i.sku} — {i.name} (Qty: {i.quantity}, Exp: {i.expiry_date.isoformat()})": i for i in all_db_items}
            selected_label = st.selectbox("Select Item to Check Out", list(item_display_map.keys()))
            selected_item = item_display_map[selected_label]

            with st.form("checkout_form"):
                qty_deduct = st.number_input("Quantity to Check Out", min_value=1, max_value=selected_item.quantity, value=1, step=1)
                auto_del = st.checkbox("Auto-remove record from database if quantity drops to 0", value=True)
                do_checkout = st.form_submit_button("Checkout Selected Stock", use_container_width=True)

                if do_checkout:
                    success, msg, remaining = inventory_service.check_out_item(
                        sku=selected_item.sku,
                        quantity_to_remove=int(qty_deduct),
                        auto_delete_if_zero=auto_del
                    )
                    if success:
                        st.success(msg)
                        st.toast("Stock successfully updated!", icon="✅")
                        st.rerun()
                    else:
                        st.error(msg)
        else:
            st.info("No items in inventory to check out.")

    with col_res2:
        st.subheader("☣️ Hazardous Safe Disposal (All Expired Items)")
        st.markdown(
            "Safely dispose of all stock whose lifespan equation evaluates to **Days Remaining <= 0**. "
            "This purges expired records in compliance with food safety and pharmaceutical regulations."
        )

        if summary.expired_items_count > 0:
            st.warning(f"Currently **{summary.expired_items_count} expired item(s)** ({summary.expired_units_count} total units) are flagged for disposal.")
            if st.button("🚨 Execute Safe Disposal of ALL Expired Items", use_container_width=True):
                deleted_count = inventory_service.bulk_dispose_expired()
                st.toast(f"Successfully disposed of {deleted_count} expired items.", icon="🗑️")
                st.rerun()
        else:
            st.success("No expired items currently in stock. All inventory is safe!")


# ------------------------------------------------------------------------------
# TAB 5: AUDIT LOGS & DISPATCHED EMAIL ALERTS
# ------------------------------------------------------------------------------
with tabs[4]:
    st.header("📧 Dispatched Email Alert Logs & Audit Trail")
    st.caption("Immutable operational audit log of emergency email broadcasts dispatched by Node 6 [AlertTrigger].")

    log_path = alert_config.log_file
    if log_path.exists():
        log_content = log_path.read_text(encoding="utf-8")
        st.text_area("Audit Trail (alerts.log)", value=log_content, height=450)
        st.download_button(
            label="📥 Download alerts.log",
            data=log_content,
            file_name="expiry_tracker_alerts.log",
            mime="text/plain",
            use_container_width=True
        )
    else:
        st.info("No alert logs recorded yet.")
