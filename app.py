import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import datetime

st.set_page_config(page_title="Advanced Expense Tracker", layout="centered")
st.title("💰 Advanced Expense Tracker")

DATA_PATH = "expenses.csv"

# -------------------- Data Functions --------------------
def load_data(path=DATA_PATH):
    try:
        return pd.read_csv(path, parse_dates=["date"])
    except FileNotFoundError:
        return pd.DataFrame(columns=["date", "category", "amount", "note"])

def save_data(df, path=DATA_PATH):
    df.to_csv(path, index=False)

df = load_data()

# -------------------- Sidebar --------------------
st.sidebar.header("📂 Data Options")

uploaded = st.sidebar.file_uploader(
    "Upload CSV (date, category, amount, note)", type=["csv"]
)

if uploaded:
    new = pd.read_csv(uploaded, parse_dates=["date"])
    required_cols = {"date", "category", "amount", "note"}

    if not required_cols.issubset(new.columns):
        st.sidebar.error("❌ Invalid CSV format")
    else:
        df = pd.concat([df, new], ignore_index=True)
        df.drop_duplicates(
            subset=["date", "category", "amount", "note"], inplace=True
        )
        save_data(df)
        st.sidebar.success("✅ CSV uploaded & duplicates removed")

if st.sidebar.button("⚠ Reset All Data"):
    df = pd.DataFrame(columns=["date", "category", "amount", "note"])
    save_data(df)
    st.sidebar.warning("All data deleted")

# -------------------- Add Expense --------------------
st.header("➕ Add Expense")

with st.form("add_expense"):
    date = st.date_input("Date", datetime.date.today())
    category = st.text_input("Category")
    amount = st.number_input("Amount", min_value=0.0, step=1.0)
    note = st.text_input("Note (optional)")
    submit = st.form_submit_button("Add Expense")

if submit:
    if not category.strip():
        st.error("❌ Category cannot be empty")
    elif amount <= 0:
        st.error("❌ Amount must be greater than 0")
    else:
        new_row = {
            "date": pd.to_datetime(date),
            "category": category.strip(),
            "amount": float(amount),
            "note": note
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df)
        st.success("✅ Expense Added")

# -------------------- Display Data --------------------
st.header("📊 Expense Records")

if df.empty:
    st.info("No data available")
else:
    st.dataframe(df.sort_values("date", ascending=False), use_container_width=True)

    # -------------------- Summary --------------------
    st.subheader("📌 Summary")

    total = df["amount"].sum()
    avg_exp = np.mean(df["amount"])
    max_exp = np.max(df["amount"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Spent", f"₹{total:.2f}")
    col2.metric("Average Expense", f"₹{avg_exp:.2f}")
    col3.metric("Highest Expense", f"₹{max_exp:.2f}")

    # -------------------- Category Summary --------------------
    st.subheader("📂 Category-wise Spending")

    by_cat = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    st.table(by_cat.reset_index())

    fig1, ax1 = plt.subplots()
    by_cat.plot.pie(autopct="%1.1f%%", ax=ax1)
    ax1.set_ylabel("")
    st.pyplot(fig1)

    # -------------------- Monthly Trend --------------------
    st.subheader("📈 Monthly Trend")

    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    monthly = df.groupby("month")["amount"].sum()

    fig2, ax2 = plt.subplots()
    ax2.plot(monthly.index, monthly.values, marker="o")
    ax2.set_xlabel("Month")
    ax2.set_ylabel("Amount")
    ax2.set_title("Monthly Spending")
    fig2.autofmt_xdate()
    st.pyplot(fig2)

    # -------------------- Delete Expense --------------------
    st.subheader("🗑 Delete Expense")

    delete_index = st.selectbox(
        "Select expense index to delete", df.index
    )

    if st.button("Delete Selected Expense"):
        df = df.drop(delete_index)
        save_data(df)
        st.success("✅ Expense Deleted")
        st.experimental_rerun()

    # -------------------- Filter & Export --------------------
    st.subheader("📤 Filter & Export")

    start_date = st.date_input("Start Date", df["date"].min().date())
    end_date = st.date_input("End Date", df["date"].max().date())

    mask = (df["date"] >= pd.to_datetime(start_date)) & (
        df["date"] <= pd.to_datetime(end_date)
    )
    filtered = df.loc[mask]

    st.write(f"Showing {len(filtered)} records")
    st.dataframe(filtered, use_container_width=True)

    st.download_button(
        "⬇ Download CSV",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name="expenses_filtered.csv",
        mime="text/csv",
    )

    def to_excel(df):
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        return buffer.getvalue()

    st.download_button(
        "⬇ Download Excel",
        to_excel(filtered),
        file_name="expenses_filtered.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
