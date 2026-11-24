import re
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st
from openpyxl.styles import Font

st.set_page_config(
    page_title="Sales Analytics Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Self-Service Sales Analytics Dashboard")
st.caption(
    "Upload a sales file from different stores. The dashboard detects common "
    "column names, lets you confirm mappings, and displays analytics supported "
    "by the uploaded data."
)

# --------------------------------------------------
# 1. FILE UPLOAD AND DATA READING
# --------------------------------------------------
uploaded_file = st.sidebar.file_uploader(
    "Upload your sales file",
    type=["csv", "xlsx"],
)

if uploaded_file is None:
    st.info("Upload a CSV or XLSX file from the sidebar to begin.")
    st.markdown(
        """
        ### What this app does
        - Detects common column-name variations automatically
        - Lets you manually map columns when needed
        - Handles optional fields such as Profit, Category, Region, Product,
          and Order ID
        - Cleans common data-quality issues
        - Creates interactive charts and business insights where possible
        - Exports filtered data and an Excel summary report
        """
    )
    st.stop()

try:
    if uploaded_file.name.lower().endswith(".csv"):
        # Try common CSV encodings because files may come from Excel,
        # Windows applications, or other systems.
        raw_bytes = uploaded_file.getvalue()
        raw_df = None
        encoding_errors = []

        for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
            try:
                from io import BytesIO
                raw_df = pd.read_csv(BytesIO(raw_bytes), encoding=encoding)
                break
            except UnicodeDecodeError as exc:
                encoding_errors.append(f"{encoding}: {exc}")

        if raw_df is None:
            st.error(
                "Could not decode this CSV using common encodings. "
                "Open it in Excel and save it as 'CSV UTF-8 (Comma delimited)'."
            )
            with st.expander("Encoding details"):
                st.code("\\n".join(encoding_errors))
            st.stop()
    else:
        raw_df = pd.read_excel(uploaded_file, engine="openpyxl")
except Exception as exc:
    st.error("Unable to read this file. Please upload a valid CSV or XLSX file.")
    st.caption(f"Technical details: {exc}")
    st.stop()

if raw_df.empty:
    st.error("The uploaded file contains no data.")
    st.stop()

raw_df.columns = [str(column).strip() for column in raw_df.columns]

if any(not column for column in raw_df.columns):
    st.error("One or more columns have empty names. Rename them and upload again.")
    st.stop()

if raw_df.columns.duplicated().any():
    st.error(
        "Duplicate column names were found. Give each column a unique name "
        "and upload the file again."
    )
    st.stop()
before_rows = len(raw_df)
before_missing = int(raw_df.isna().sum().sum())
duplicate_count = int(raw_df.duplicated().sum())

st.success(f"Loaded {before_rows:,} rows and {len(raw_df.columns):,} columns.")
with st.expander("Preview uploaded data"):
    st.dataframe(raw_df.head(20), use_container_width=True)

# --------------------------------------------------
# 2. AUTOMATIC COLUMN DETECTION + MANUAL MAPPING
# --------------------------------------------------
def normalize_name(value):
    """Normalize names so Order_Date, order date and order-date match."""
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


ALIASES = {
    "Date": [
        "date", "order_date", "orderdate", "invoice_date", "invoicedate",
        "transaction_date", "sales_date", "created_date", "purchase_date",
        "ship_date",
    ],
    "Sales": [
        "sales", "revenue", "amount", "total_sales", "net_sales",
        "sales_amount", "total_revenue", "revenue_amount", "order_value",
        "gross_sales", "turnover",
    ],
    "Profit": [
        "profit", "net_profit", "total_profit", "profit_amount",
        "profit_loss", "earnings", "margin_amount",
    ],
    "Category": [
        "category", "product_category", "product_type", "department",
        "item_category", "class",
    ],
    "Region": [
        "region", "sales_region", "territory", "zone", "area", "state",
        "province", "market",
    ],
    "Product": [
        "product", "product_name", "item", "item_name", "product_description",
        "sku", "product_id", "item_description",
    ],
    "Order ID": [
        "order_id", "orderid", "order_number", "invoice_id", "invoiceid",
        "invoice_number", "transaction_id", "order_no", "receipt_id",
    ],
}

def detect_column(available_columns, role):
    """Return the best exact normalized alias match, if any."""
    normalized_columns = {}
    for col in available_columns:
        normalized_columns.setdefault(normalize_name(col), col)

    for alias in ALIASES[role]:
        match = normalized_columns.get(normalize_name(alias))
        if match is not None:
            return match
    return "-- Not mapped --"


st.sidebar.header("Column Mapping")
st.sidebar.caption(
    "Suggestions are automatic. Check them before using the dashboard. "
    "Only Date and Sales are required."
)

columns = list(raw_df.columns)
placeholder = "-- Not mapped --"
options = [placeholder] + columns


def mapping_selector(role, label, required=False):
    suggestion = detect_column(columns, role)
    default_index = options.index(suggestion) if suggestion in options else 0
    return st.sidebar.selectbox(
        f"{label}{' (required)' if required else ' (optional)'}",
        options,
        index=default_index,
        key=f"map_{role.lower().replace(' ', '_')}",
    )


date_col = mapping_selector("Date", "Date column", required=True)
sales_col = mapping_selector("Sales", "Sales / Revenue column", required=True)
profit_col = mapping_selector("Profit", "Profit column")
category_col = mapping_selector("Category", "Category / Department column")
region_col = mapping_selector("Region", "Region / Territory column")
product_col = mapping_selector("Product", "Product / Item column")
order_col = mapping_selector("Order ID", "Order / Invoice ID column")

required_mappings = {"Date": date_col, "Sales": sales_col}
if any(value == placeholder for value in required_mappings.values()):
    st.warning(
        "Map both Date and Sales in the sidebar to continue. Other fields are optional."
    )
    st.stop()

# A source column cannot represent two different roles.
selected_roles = [
    value for value in [
        date_col, sales_col, profit_col, category_col,
        region_col, product_col, order_col
    ] if value != placeholder
]
if len(selected_roles) != len(set(selected_roles)):
    st.error(
        "The same source column is assigned to more than one role. "
        "Choose a different column for each mapped role."
    )
    st.stop()
# --------------------------------------------------
# 3. STANDARDIZE DATA AND CLEAN COMMON ISSUES
# --------------------------------------------------
df = pd.DataFrame(index=raw_df.index)
df["Date"] = raw_df[date_col]
df["Sales"] = raw_df[sales_col]

if profit_col != placeholder:
    df["Profit"] = raw_df[profit_col]
if category_col != placeholder:
    df["Category"] = raw_df[category_col]
if region_col != placeholder:
    df["Region"] = raw_df[region_col]
if product_col != placeholder:
    df["Product"] = raw_df[product_col]
if order_col != placeholder:
    df["Order ID"] = raw_df[order_col]

# Parse dates. dayfirst=True supports common DD-MM-YYYY / DD/MM/YYYY files.
# If the store uses a different date format, the user should verify the result.
df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)

def parse_numeric(series):
    """Convert numeric strings, including common currency symbols/commas."""
    cleaned = (
        series.astype("string")
        .str.replace(r"[$£€₹,\s]", "", regex=True)
        .str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    )
    return pd.to_numeric(cleaned, errors="coerce")


df["Sales"] = parse_numeric(df["Sales"])
if "Profit" in df.columns:
    df["Profit"] = parse_numeric(df["Profit"])

for col in ["Category", "Region", "Product", "Order ID"]:
    if col in df.columns:
        df[col] = df[col].astype("string").str.strip()
        df[col] = df[col].replace("", pd.NA)

# Remove duplicate rows based on the original uploaded data.
duplicate_mask = raw_df.duplicated()
df = df.loc[~duplicate_mask].copy()
duplicate_count = int(duplicate_mask.sum())

# Date and Sales are the only mandatory valid fields.
invalid_required = df["Date"].isna() | df["Sales"].isna()
invalid_required_count = int(invalid_required.sum())
df = df.loc[~invalid_required].copy()

for col in ["Category", "Region", "Product", "Order ID"]:
    if col in df.columns:
        df[col] = df[col].fillna("Unknown")

if df.empty:
    st.error(
        "No usable rows remain after cleaning. Check your Date and Sales mappings "
        "and confirm that those columns contain valid values."
    )
    st.stop()

after_rows = len(df)
after_missing = int(df.isna().sum().sum())
# --------------------------------------------------
# 4. DATA QUALITY REPORT
# --------------------------------------------------
st.subheader("Data Quality Report")
q1, q2, q3, q4 = st.columns(4)
q1.metric("Original rows", f"{before_rows:,}")
q2.metric("Rows after cleaning", f"{after_rows:,}")
q3.metric("Duplicate rows removed", f"{duplicate_count:,}")
q4.metric("Invalid Date/Sales rows removed", f"{invalid_required_count:,}")

with st.expander("View cleaning details"):
    quality_df = pd.DataFrame({
        "Metric": [
            "Rows before cleaning",
            "Missing cells in uploaded data",
            "Duplicate rows removed",
            "Rows removed for invalid Date/Sales",
            "Rows after cleaning",
            "Missing cells in standardized data",
        ],
        "Count": [
            before_rows, before_missing, duplicate_count,
            invalid_required_count, after_rows, after_missing,
        ],
    })
    st.dataframe(quality_df, hide_index=True, use_container_width=True)
    st.caption(
        "Date and Sales are required. Profit, Category, Region, Product and Order ID "
        "are optional; analytics that need an unmapped field are skipped."
    )

# --------------------------------------------------
# 5. FILTERS - ONLY SHOW AVAILABLE DIMENSIONS
# --------------------------------------------------
st.sidebar.header("Dashboard Filters")
min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

filtered_df = df.copy()

if "Category" in df.columns:
    categories = sorted(df["Category"].dropna().unique().tolist())
    selected_categories = st.sidebar.multiselect(
        "Category", categories, default=categories
    )
    filtered_df = filtered_df[filtered_df["Category"].isin(selected_categories)]

if "Region" in df.columns:
    regions = sorted(df["Region"].dropna().unique().tolist())
    selected_regions = st.sidebar.multiselect(
        "Region / Territory", regions, default=regions
    )
    filtered_df = filtered_df[filtered_df["Region"].isin(selected_regions)]

if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Select both a start date and an end date.")
    st.stop()

start_date, end_date = date_range
if start_date > end_date:
    st.error("The start date must be on or before the end date.")
    st.stop()

filtered_df = filtered_df[
    (filtered_df["Date"].dt.date >= start_date)
    & (filtered_df["Date"].dt.date <= end_date)
].copy()

if filtered_df.empty:
    st.warning("No records match the selected filters.")
    st.stop()


# --------------------------------------------------
# 6. KPIs - SHOW ONLY WHAT THE DATA SUPPORTS
# --------------------------------------------------
total_sales = float(filtered_df["Sales"].sum())
total_profit = float(filtered_df["Profit"].sum()) if "Profit" in filtered_df.columns else None

profit_margin = None
if total_profit is not None and total_sales != 0:
    profit_margin = total_profit / total_sales * 100

total_orders = None
average_order_value = None
if "Order ID" in filtered_df.columns:
    valid_orders = filtered_df.loc[
        filtered_df["Order ID"] != "Unknown", "Order ID"
    ]
    total_orders = int(valid_orders.nunique())
    if total_orders > 0:
        average_order_value = total_sales / total_orders

monthly = filtered_df.set_index("Date")["Sales"].resample("MS").sum()
monthly_growth = None
if len(monthly) >= 2 and monthly.iloc[-2] != 0:
    monthly_growth = (
        (monthly.iloc[-1] - monthly.iloc[-2]) / abs(monthly.iloc[-2]) * 100
    )

st.subheader("Key Performance Indicators")
kpi_items = [("Total Sales", f"{total_sales:,.2f}")]
if total_profit is not None:
    kpi_items.append(("Total Profit", f"{total_profit:,.2f}"))
if profit_margin is not None:
    kpi_items.append(("Profit Margin", f"{profit_margin:.2f}%"))
if total_orders is not None:
    kpi_items.append(("Total Orders", f"{total_orders:,}"))
if average_order_value is not None:
    kpi_items.append(("Average Order Value", f"{average_order_value:,.2f}"))
if monthly_growth is not None:
    kpi_items.append(("Latest Month MoM Growth", f"{monthly_growth:+.2f}%"))

for start in range(0, len(kpi_items), 3):
    metric_columns = st.columns(min(3, len(kpi_items) - start))
    for column, (label, value) in zip(metric_columns, kpi_items[start:start + 3]):
        column.metric(label, value)

st.caption(
    "Sales and profit use the monetary units in your file. Order-based KPIs appear "
    "only when an Order ID / Invoice ID column is mapped. Profit KPIs appear only "
    "when a Profit column is mapped."
)

# --------------------------------------------------
# 7. INTERACTIVE CHARTS - CONDITIONAL ON AVAILABLE FIELDS
# --------------------------------------------------
st.subheader("Sales Performance")

monthly_df = monthly.rename("Sales").reset_index()
monthly_df.columns = ["Month", "Sales"]
fig_monthly = px.line(
    monthly_df, x="Month", y="Sales", markers=True,
    title="Monthly Sales Trend",
)
st.plotly_chart(fig_monthly, use_container_width=True)

if "Product" in filtered_df.columns:
    product_sales = filtered_df.groupby("Product", as_index=False).agg(
        Sales=("Sales", "sum")
    )
    if "Profit" in filtered_df.columns:
        product_profit = filtered_df.groupby("Product", as_index=False).agg(
            Profit=("Profit", "sum")
        )
        product_sales = product_sales.merge(product_profit, on="Product", how="left")

    top10 = product_sales.nlargest(10, "Sales").sort_values("Sales")
    bottom10 = product_sales.nsmallest(10, "Sales").sort_values("Sales")
    left, right = st.columns(2)
    with left:
        fig_top = px.bar(
            top10, x="Sales", y="Product", orientation="h",
            title="Top 10 Products by Sales",
        )
        st.plotly_chart(fig_top, use_container_width=True)
    with right:
        fig_bottom = px.bar(
            bottom10, x="Sales", y="Product", orientation="h",
            title="Bottom 10 Products by Sales",
        )
        st.plotly_chart(fig_bottom, use_container_width=True)
else:
    st.info("Map a Product / Item column to display top and bottom product charts.")

if "Category" in filtered_df.columns:
    category_sales = filtered_df.groupby("Category", as_index=False)["Sales"].sum()
    fig_category = px.pie(
        category_sales, names="Category", values="Sales",
        title="Sales Share by Category", hole=0.4,
    )
    st.plotly_chart(fig_category, use_container_width=True)

if "Region" in filtered_df.columns and "Category" in filtered_df.columns:
    region_category = filtered_df.pivot_table(
        index="Region", columns="Category", values="Sales",
        aggfunc="sum", fill_value=0,
    )
    fig_heatmap = px.imshow(
        region_category, text_auto=".2s", aspect="auto",
        title="Sales Heatmap: Region vs Category",
        labels={"x": "Category", "y": "Region", "color": "Sales"},
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)
    st.caption(
        "This is a region-category matrix heatmap, not a geographic map."
    )


# --------------------------------------------------
# 8. RULE-BASED BUSINESS INSIGHTS
# --------------------------------------------------
st.subheader("Business Insights")
insights = []

if monthly_growth is not None:
    if monthly_growth >= 10:
        insights.append(
            f"Sales grew strongly by {monthly_growth:.1f}% in the latest month "
            "compared with the previous month."
        )
    elif monthly_growth > 0:
        insights.append(f"Sales increased by {monthly_growth:.1f}% in the latest month.")
    elif monthly_growth < 0:
        insights.append(f"Sales declined by {abs(monthly_growth):.1f}% in the latest month.")
    else:
        insights.append("Sales were unchanged in the latest month.")
else:
    insights.append(
        "Monthly growth is unavailable: at least two calendar months and a "
        "nonzero previous-month sales total are needed."
    )

if total_profit is not None:
    if profit_margin is not None:
        insights.append(f"Overall profit margin for the selected data is {profit_margin:.1f}%.")
    if total_profit < 0:
        insights.append(
            "Overall profit is negative for the selected filters. Review costs, "
            "discounts, returns and sales mix."
        )
    if "Category" in filtered_df.columns:
        category_profit = filtered_df.groupby("Category").agg(
            Sales=("Sales", "sum"), Profit=("Profit", "sum")
        )
        category_profit["Margin"] = (
            category_profit["Profit"]
            .div(category_profit["Sales"].where(category_profit["Sales"] != 0))
            * 100
        )
        valid_margins = category_profit["Margin"].dropna()
        if not valid_margins.empty:
            lowest_category = valid_margins.idxmin()
            insights.append(
                f"{lowest_category} has the lowest category profit margin "
                f"at {valid_margins.min():.1f}%."
            )
    if "Product" in filtered_df.columns:
        product_profit = filtered_df.groupby("Product")["Profit"].sum()
        loss_products = int((product_profit < 0).sum())
        insights.append(
            f"{loss_products} products have negative total profit within the selected filters."
        )
else:
    insights.append(
        "Profit-based insights are hidden because no Profit column is mapped."
    )

if "Category" in filtered_df.columns:
    best_category = filtered_df.groupby("Category")["Sales"].sum().idxmax()
    insights.append(f"{best_category} is the highest-sales category in the selected data.")
if "Region" in filtered_df.columns:
    best_region = filtered_df.groupby("Region")["Sales"].sum().idxmax()
    insights.append(f"{best_region} is the highest-sales region / territory in the selected data.")
if total_sales < 0:
    insights.append(
        "Total sales are negative. Check whether the source includes returns, "
        "credit notes, or other negative transactions."
    )

for insight in insights:
    st.markdown(f"- {insight}")

with st.expander("How the insight rules work"):
    st.markdown(
        """
        - Strong monthly growth: 10% or more.
        - Positive growth: greater than 0% but below 10%.
        - Declining sales: below 0%.
        - Profit insights are generated only when a Profit column is available.
        - Category, region and product insights appear only when those fields are mapped.
        - Undefined profit margin is not shown when total sales are zero.
        """
    )

# --------------------------------------------------
# 9. FILTERED DATA EXPORT
# --------------------------------------------------
st.subheader("Download Reports")
csv_data = filtered_df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="Download Filtered Data (CSV)",
    data=csv_data,
    file_name="filtered_sales_data.csv",
    mime="text/csv",
)

# --------------------------------------------------
# 10. FORMATTED EXCEL SUMMARY REPORT
# --------------------------------------------------
def create_excel_report(data, insights_list, kpis):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        data.to_excel(writer, sheet_name="Filtered Data", index=False)
        pd.DataFrame({
            "KPI": list(kpis.keys()),
            "Value": list(kpis.values()),
        }).to_excel(writer, sheet_name="Summary", index=False)
        pd.DataFrame({
            "Business Insights": insights_list,
        }).to_excel(writer, sheet_name="Insights", index=False)

        workbook = writer.book
        for sheet in workbook.worksheets:
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for cell in sheet[1]:
                cell.font = Font(bold=True)
            for column_cells in sheet.columns:
                max_length = max(len(str(cell.value or "")) for cell in column_cells)
                letter = column_cells[0].column_letter
                sheet.column_dimensions[letter].width = min(max(max_length + 2, 12), 45)
    return output.getvalue()


kpis = {label: value for label, value in kpi_items}
kpis["Filtered Rows"] = len(filtered_df)
excel_file = create_excel_report(filtered_df, insights, kpis)

st.download_button(
    label="Download Excel Summary Report",
    data=excel_file,
    file_name="sales_analytics_report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.divider()
st.caption("Sales Analytics Dashboard | Python • Pandas • Plotly • Streamlit")
