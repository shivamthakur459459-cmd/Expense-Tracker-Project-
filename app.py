import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import datetime
from io import BytesIO

# ==========================
# 🔒 PASSWORD PROTECTION CODE
# ==========================
# Default password if not set in secrets
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "Shivam@123")

if "authed" not in st.session_state:
    st.session_state.authed = False

if not st.session_state.authed:
    pwd = st.text_input("Enter app password", type="password")
    if st.button("Unlock"):
        if pwd == APP_PASSWORD:
            st.session_state.authed = True
            st.rerun()
        else:
            st.error("Incorrect password")
    st.stop()
# ==========================

# ✅ App starts only after password unlock
st.set_page_config(page_title="Expense Tracker", layout="centered")
st.title("💰 Expense Tracker")

DATA_PATH = "expenses.csv"

# Load & Save Functions
def load_data(path=DATA_PATH):
    try:
        df = pd.read_csv(path, parse_dates=["date"])
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=["date", "category", "amount", "note"])

def save_data(df, path=DATA_PATH):
    df.to_csv(path, index=False)

df = load_data()

# Sidebar
st.sidebar.header("📂 Options")

uploaded = st.sidebar.file_uploader("Upload CSV (date,category,amount,note)", type=["csv"])
if uploaded:
    new = pd.read_csv(uploaded, parse_dates=["date"])
    df = pd.concat([df, new], ignore_index=True)
    save_data(df)
    st.sidebar.success("✅ File merged successfully!")

if st.sidebar.button("🧹 Reset all data"):
    df = pd.DataFrame(columns=["date", "category", "amount", "note"])
    save_data(df)
    st.sidebar.warning("All data cleared!")

# Add new expense
st.header("➕ Add Expense")
with st.form("add_expense"):
    date = st.date_input("Date", datetime.date.today())
    category = st.text_input("Category")
    amount = st.number_input("Amount (₹)", min_value=0.0, step=1.0)
    note = st.text_input("Note (optional)")
    submitted = st.form_submit_button("Add")
if submitted:
    new_row = {
        "date": pd.to_datetime(date),
        "category": category.strip() or "Misc",
        "amount": float(amount),
        "note": note,
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_data(df)
    st.success("Expense added successfully!")

# Show data
st.header("📊 All Expenses")
if df.empty:
    st.info("No expenses yet. Add one above.")
else:
    df['date'] = pd.to_datetime(df['date'])
    st.dataframe(df.sort_values("date", ascending=False), use_container_width=True)

    # Summary
    st.subheader("📈 Summary")
    total = df["amount"].sum()
    month_total = df[df['date'].dt.to_period("M") == pd.Period(datetime.date.today(), "M")]["amount"].sum()
    st.metric("Total Spent", f"₹{total:.2f}")
    st.metric("This Month", f"₹{month_total:.2f}")

    # By category
    st.subheader("📦 By Category")
    by_cat = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    st.table(by_cat.reset_index().rename(columns={"amount": "Total"}))

    # Pie chart
    fig1, ax1 = plt.subplots()
    by_cat.plot.pie(autopct="%1.1f%%", ax=ax1)
    ax1.set_ylabel("")
    st.pyplot(fig1)

    # Monthly trend
    st.subheader("📅 Monthly Trend")
    df['month'] = df['date'].dt.to_period("M").dt.to_timestamp()
    monthly = df.groupby("month")["amount"].sum().reset_index()
    fig2, ax2 = plt.subplots()
    ax2.plot(monthly['month'], monthly['amount'], marker='o')
    ax2.set_xlabel("Month")
    ax2.set_ylabel("Amount (₹)")
    ax2.set_title("Spending Over Time")
    fig2.autofmt_xdate()
    st.pyplot(fig2)

    # Filter & Export
    st.subheader("🔍 Filter & Export")
    start_col, end_col = st.columns(2)
    start_date = start_col.date_input("Start date", df['date'].min().date())
    end_date = end_col.date_input("End date", df['date'].max().date())
    mask = (df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))
    filtered = df.loc[mask]

    st.write(f"Showing {len(filtered)} records")
    st.dataframe(filtered)# CSV export
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", csv, "filtered_expenses.csv", "text/csv")

    # Excel export
    def to_excel_bytes(df):
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Expenses")
        buffer.seek(0)
        return buffer.getvalue()

    st.download_button(
        "⬇️ Download Excel (.xlsx)",
        to_excel_bytes(filtered),
        "filtered_expenses.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
