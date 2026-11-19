"""
==============================================================================
MODULE: app_streamlit.py
DESCRIPTION: Interactive Web Dashboard for Product Expiry & FIFO Inventory.
==============================================================================
"""

import os
from datetime import date, datetime
import pandas as pd
import streamlit as st

from inventory_service import InventoryService
from gemini_extractor import GeminiExtractor
from models import InventoryItem, ExpiryStatus, RecommendedAction

# Page configuration
st.set_page_config(
    page_title="Product Expiry & FIFO Tracking System",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        padding: 16px;
        border-radius: 10px;
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        text-align: center;
    }
    .badge-safe { background-color: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 6px; font-weight: bold; }
    .badge-near { background-color: #fef9c3; color: #854d0e; padding: 4px 8px; border-radius: 6px; font-weight: bold; }
    .badge-expired { background-color: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 6px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_services():
    service = InventoryService()
    extractor = GeminiExtractor()
    return service, extractor


service, extractor = get_services()

# Header
st.title("📦 Product Expiry Tracking & FIFO Inventory System")
st.caption("AI-Powered Expiry Detection • Automated FIFO Priority • Waste Prevention Engine")

# Load Inventory
items = service.get_fifo_prioritized_inventory()
eval_items = [service.lifespan_engine.evaluate(item) for item in items]

# Summary Metrics
total_count = len(eval_items)
safe_count = sum(1 for i in eval_items if i.status == ExpiryStatus.SAFE)
near_count = sum(1 for i in eval_items if i.status == ExpiryStatus.NEAR_EXPIRY)
expired_count = sum(1 for i in eval_items if i.status == ExpiryStatus.EXPIRED)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Tracked Items", total_count)
col2.metric("🟢 Safe Stock", safe_count)
col3.metric("🟡 Near Expiry (Action Req.)", near_count)
col4.metric("🔴 Expired (Dispose)", expired_count)

st.markdown("---")

# Main Navigation Tabs
tab_dash, tab_scan, tab_add, tab_actions = st.tabs([
    "📊 FIFO Inventory Table",
    "📷 AI / OCR Label Scanner",
    "➕ Manual Stock Entry",
    "⚡ Stock Checkout & Disposal"
])

# ----------------------------------------------------------------------------
# TAB 1: FIFO Inventory Table
# ----------------------------------------------------------------------------
with tab_dash:
    st.subheader("Real-Time Inventory (Sorted by Earliest Expiry / FIFO)")
    
    if not eval_items:
        st.info("No products currently in inventory. Add an item or scan a label to get started!")
    else:
        table_data = []
        for i in eval_items:
            table_data.append({
                "SKU": i.item.sku,
                "Product Name": i.item.name,
                "Category": i.item.category,
                "Quantity": i.item.quantity,
                "Expiry Date": str(i.item.expiry_date),
                "Days Remaining": i.days_remaining,
                "Status": i.status.value,
                "Action": i.recommended_action.value
            })
        
        df = pd.DataFrame(table_data)
        
        # Filter options
        status_filter = st.multiselect(
            "Filter by Status:",
            options=[ExpiryStatus.SAFE.value, ExpiryStatus.NEAR_EXPIRY.value, ExpiryStatus.EXPIRED.value],
            default=[ExpiryStatus.SAFE.value, ExpiryStatus.NEAR_EXPIRY.value, ExpiryStatus.EXPIRED.value]
        )
        
        filtered_df = df[df["Status"].isin(status_filter)]
        st.dataframe(filtered_df, use_container_width=True)

# ----------------------------------------------------------------------------
# TAB 2: AI / OCR Label Scanner
# ----------------------------------------------------------------------------
with tab_scan:
    st.subheader("Scan Product Label using Gemini Vision AI / OCR")
    st.write("Upload a packaging photo or paste raw OCR text from a handheld scanner.")

    scan_mode = st.radio("Input Format:", ["Upload Label Image", "Paste Raw OCR Text"], horizontal=True)

    if scan_mode == "Upload Label Image":
        uploaded_file = st.file_uploader("Upload product packaging photo (JPG, PNG)", type=["jpg", "jpeg", "png"])
        if uploaded_file is not None:
            image_bytes = uploaded_file.read()
            st.image(image_bytes, caption="Uploaded Packaging Image", width=320)
            
            if st.button("🔍 Extract Expiry & Product Info with AI", type="primary"):
                with st.spinner("Analyzing image label with Gemini 2.5 Flash..."):
                    result = extractor.extract_from_image(image_bytes, mime_type=uploaded_file.type)
                    st.success("Extraction Complete!")
                    
                    st.json({
                        "Product Name": result.name,
                        "SKU": result.sku,
                        "Category": result.category,
                        "Expiry Date": str(result.expiry_date),
                        "Quantity": result.quantity,
                        "Confidence Score": f"{result.confidence * 100:.1f}%"
                    })
                    
                    if st.button("📥 Save Extracted Product to Database"):
                        item = InventoryItem(
                            sku=result.sku,
                            name=result.name,
                            category=result.category,
                            expiry_date=result.expiry_date,
                            quantity=result.quantity
                        )
                        service.add_item(item)
                        st.success(f"Item {result.sku} saved to inventory!")
                        st.rerun()

    else:
        ocr_text = st.text_area(
            "Paste OCR Text Stream:",
            value="LOT# MLK-9021 FRESH MILK 1L\nMFG: 2026-01-10\nBEST BEFORE: 2026-10-25\nQTY: 10",
            height=120
        )
        if st.button("🔍 Parse & Extract with AI", type="primary"):
            with st.spinner("Extracting product information..."):
                result = extractor.extract_from_text(ocr_text)
                st.success("Extraction Complete!")
                st.write(f"**Detected Product:** {result.name}")
                st.write(f"**SKU:** `{result.sku}` | **Category:** {result.category}")
                st.write(f"**Expiry Date:** `{result.expiry_date}` | **Quantity:** {result.quantity}")
                
                if st.button("📥 Commit Parsed Item to Inventory"):
                    item = InventoryItem(
                        sku=result.sku,
                        name=result.name,
                        category=result.category,
                        expiry_date=result.expiry_date,
                        quantity=result.quantity
                    )
                    service.add_item(item)
                    st.success(f"Added {result.sku} to database!")
                    st.rerun()

# ----------------------------------------------------------------------------
# TAB 3: Manual Stock Entry
# ----------------------------------------------------------------------------
with tab_add:
    st.subheader("Manual Inventory Registration")
    with st.form("manual_entry_form"):
        f_sku = st.text_input("Product SKU:", placeholder="e.g. YOG-1002")
        f_name = st.text_input("Product Name:", placeholder="e.g. Greek Vanilla Yogurt 500g")
        f_cat = st.selectbox("Category:", ["Dairy", "Bakery", "Beverages", "Produce", "Meat & Seafood", "Pharmacy", "Pantry", "General"])
        f_date = st.date_input("Expiry Date:", value=date.today())
        f_qty = st.number_input("Quantity in Units:", min_value=1, value=10, step=1)
        
        submitted = st.form_submit_button("Save Item to Inventory")
        if submitted:
            if not f_sku or not f_name:
                st.error("Please provide both SKU and Product Name.")
            else:
                new_item = InventoryItem(
                    sku=f_sku.strip(),
                    name=f_name.strip(),
                    category=f_cat,
                    expiry_date=f_date,
                    quantity=int(f_qty)
                )
                service.add_item(new_item)
                st.success(f"Successfully registered {f_name} (SKU: {f_sku})!")
                st.rerun()

# ----------------------------------------------------------------------------
# TAB 4: Stock Checkout & Safe Disposal
# ----------------------------------------------------------------------------
with tab_actions:
    st.subheader("Inventory Deduction & Safe Waste Disposal")
    
    if items:
        sku_list = [i.sku for i in items]
        selected_sku = st.selectbox("Select SKU to Action:", sku_list)
        selected_item = next((i for i in items if i.sku == selected_sku), None)
        
        if selected_item:
            st.info(f"Selected: **{selected_item.name}** | Current Available Stock: **{selected_item.quantity}** | Expiry: **{selected_item.expiry_date}**")
            
            action_type = st.radio("Select Action:", ["Record Retail Sale (Reduce Stock)", "Safe Disposal (Remove Expired Stock)"], horizontal=True)
            
            if "Sale" in action_type:
                deduct_qty = st.number_input("Sold Quantity:", min_value=1, max_value=selected_item.quantity, value=1)
                if st.button("Confirm Sale"):
                    service.checkout_item(selected_sku, quantity=int(deduct_qty))
                    st.success(f"Recorded sale of {deduct_qty} units of {selected_sku}!")
                    st.rerun()
            else:
                if st.button("Confirm Disposal / Removal from Inventory", type="primary"):
                    service.checkout_item(selected_sku, quantity=selected_item.quantity)
                    st.warning(f"All stock for {selected_sku} marked disposed and cleared.")
                    st.rerun()
    else:
        st.write("No items available for checkout.")
