
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import datetime

st.set_page_config(page_title="Simple Expense Tracker", layout="centered")

st.title("Simple Expense Tracker")

DATA_PATH = "expenses.csv"

def load_data(path=DATA_PATH):
    try:
        df = pd.read_csv(path, parse_dates=["date"])
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=["date","category","amount","note"])

def save_data(df, path=DATA_PATH):
    df.to_csv(path, index=False)

df = load_data()

# Sidebar: upload or download
st.sidebar.header("Data Options")
uploaded = st.sidebar.file_uploader("Upload CSV (date,category,amount,note)", type=["csv"])
if uploaded:
    new = pd.read_csv(uploaded, parse_dates=["date"])
    df = pd.concat([df, new], ignore_index=True)
    save_data(df)
    st.sidebar.success("Uploaded and merged.")

if st.sidebar.button("Reset data (delete)"):
    df = pd.DataFrame(columns=["date","category","amount","note"])
    save_data(df)
    st.sidebar.warning("Data reset.")

# Add expense form
st.header("Add expense")
with st.form("add"):
    date = st.date_input("Date", value=datetime.date.today())
    cat = st.text_input("Category", value="")
    amt = st.number_input("Amount", min_value=0.0, step=1.0)
    note = st.text_input("Note (optional)")
    submitted = st.form_submit_button("Add")
if submitted:
    new_row = {"date": pd.to_datetime(date), "category": cat.strip() or "Misc", "amount": float(amt), "note": note}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_data(df)
    st.success("Added!")

st.header("Expenses")
if df.empty:
    st.info("No expenses yet. Add one above or upload a CSV.")
else:
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    st.dataframe(df.sort_values("date", ascending=False), use_container_width=True)

    # Summary metrics
    st.subheader("Summary")
    total = df["amount"].sum()
    month_total = df[df['date'].dt.to_period("M") == pd.Period(pd.Timestamp.today(), "M")]["amount"].sum()
    st.metric("Total spent (all time)", f"₹{total:.2f}")
    st.metric("This month's spent", f"₹{month_total:.2f}")

    # By category
    st.subheader("By category")
    by_cat = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    st.table(by_cat.reset_index().rename(columns={"amount":"total"}))

    # Pie chart for categories
    fig1, ax1 = plt.subplots()
    by_cat.plot.pie(autopct="%1.1f%%", ax=ax1)
    ax1.set_ylabel("")
    st.pyplot(fig1)

    # Monthly trend
    st.subheader("Monthly trend")
    df['month'] = df['date'].dt.to_period("M").dt.to_timestamp()
    monthly = df.groupby('month')['amount'].sum().reset_index()
    fig2, ax2 = plt.subplots()
    ax2.plot(monthly['month'], monthly['amount'], marker='o')
    ax2.set_xlabel("Month")
    ax2.set_ylabel("Amount")
    ax2.set_title("Monthly spending")
    fig2.autofmt_xdate()
    st.pyplot(fig2)

    # Filter and export
    st.subheader("Filter & export")
    start, end = st.columns(2)
    start_date = start.date_input("Start date", value=df['date'].min().date())
    end_date = end.date_input("End date", value=df['date'].max().date())
    mask = (df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))
    filtered = df.loc[mask]
    st.write(f"Showing {len(filtered)} rows")
    st.dataframe(filtered)

    # CSV download
    csv = filtered.to_csv(index=False).encode('utf-8')
    st.download_button("Download filtered CSV", csv, file_name="expenses_filtered.csv", mime="text/csv")

    # Excel export
    def to_excel_bytes(df):
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Expenses")
            writer.save()
        buffer.seek(0)
        return buffer.getvalue()

    st.download_button("Export filtered Excel (.xlsx)", to_excel_bytes(filtered), file_name="expenses_filtered.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
