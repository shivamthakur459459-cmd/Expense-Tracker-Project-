import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import datetime

# ---------------- Page Config ----------------
st.set_page_config(page_title="Expense Tracker", layout="centered")
st.title("💰 Simple Expense Tracker")

DATA_FILE = "expenses.csv"

# ---------------- Functions ----------------
def load_data():
    try:
        return pd.read_csv(DATA_FILE, parse_dates=["date"])
    except FileNotFoundError:
        return pd.DataFrame(columns=["date", "category", "amount", "note"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

df = load_data()

# ---------------- Sidebar ----------------
st.sidebar.header("📂 Data Options")

uploaded = st.sidebar.file_uploader(
    "Upload CSV (date, category, amount, note)", type=["csv"]
)

if uploaded:
    new_df = pd.read_csv(uploaded, parse_dates=["date"])
    required_cols = {"date", "category", "amount", "note"}

    if not required_cols.issubset(new_df.columns):
        st.sidebar.error("❌ CSV format wrong")
    else:
        df = pd.concat([df, new_df], ignore_index=True)
        df.drop_duplicates(inplace=True)
        save_data(df)
        st.sidebar.success("✅ CSV uploaded")

if st.sidebar.button("⚠ Reset All Data"):
    df = pd.DataFrame(columns=["date", "category", "amount", "note"])
    save_data(df)
    st.sidebar.warning("All data deleted")

# ---------------- Add Expense ----------------
st.header("➕ Add Expense")

with st.form("add_expense"):
    date = st.date_input("Date", datetime.date.today())
    categories = ["Food", "Travel", "Rent", "Shopping", "Other"]
    category = st.selectbox("Category", categories)
    amount = st.number_input("Amount", min_value=0.0, step=1.0)
    note = st.text_input("Note (optional)")
    submit = st.form_submit_button("Add Expense")

if submit:
    if amount <= 0:
        st.error("❌ Amount must be greater than 0")
    else:
        new_row = {
            "date": pd.to_datetime(date),
            "category": category,
            "amount": float(amount),
            "note": note
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df)
        st.success("✅ Expense Added")

# ---------------- Display Data ----------------
st.header("📊 Expenses")

if df.empty:
    st.info("No expenses found")
else:
    st.dataframe(df.sort_values("date", ascending=False), use_container_width=True)

    # ---------------- Summary ----------------
    st.subheader("📌 Summary")

    total = df["amount"].sum()
    avg_exp = np.mean(df["amount"])
    max_exp = np.max(df["amount"])

    current_month = pd.Timestamp.today().to_period("M")
    monthly_total = df[df["date"].dt.to_period("M") == current_month]["amount"].sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Spent", f"₹{total:.2f}")
    col2.metric("Average Expense", f"₹{avg_exp:.2f}")
    col3.metric("Highest Expense", f"₹{max_exp:.2f}")
    col4.metric("This Month", f"₹{monthly_total:.2f}")

    # ---------------- Budget ----------------
    st.subheader("💡 Monthly Budget")

    budget = st.number_input("Set Monthly Budget", value=5000)

    if monthly_total > budget:
        st.warning("⚠ Budget exceeded")
    else:
        st.success("✅ Budget under control")

    # ---------------- Category Chart ----------------
    st.subheader("📂 Category-wise Spending")

    by_cat = df.groupby("category")["amount"].sum()
    fig1, ax1 = plt.subplots()
    by_cat.plot(kind="bar", ax=ax1)
    ax1.set_ylabel("Amount")
    ax1.set_xlabel("Category")
    st.pyplot(fig1)

    # ---------------- Monthly Trend ----------------
    st.subheader("📈 Monthly Trend")

    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    monthly = df.groupby("month")["amount"].sum()

    fig2, ax2 = plt.subplots()
    ax2.plot(monthly.index, monthly.values, marker="o")
    ax2.set_xlabel("Month")
    ax2.set_ylabel("Amount")
    st.pyplot(fig2)

    # ---------------- Filter & Export ----------------
    st.subheader("📤 Filter & Export")

    start_date = st.date_input("Start Date", df["date"].min().date())
    end_date = st.date_input("End Date", df["date"].max().date())

    mask = (df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))
    filtered = df.loc[mask]

    st.dataframe(filtered, use_container_width=True)

    st.download_button(
        "⬇ Download CSV",
        filtered.to_csv(index=False).encode("utf-8"),
        "expenses_filtered.csv",
        "text/csv"
    )

    def to_excel(data):
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            data.to_excel(writer, index=False)
        return buffer.getvalue()

    st.download_button(
        "⬇ Download Excel",
        to_excel(filtered),
        "expenses_filtered.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
