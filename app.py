import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime

# ---------------- Page Config ----------------
st.set_page_config(page_title="Multi User Expense Tracker", layout="centered")
st.title("💰 Multi-User Expense Tracker")

DB_NAME = "expenses.db"

# ---------------- Database ----------------
def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def create_tables():
    conn = get_conn()
    cur = conn.cursor()

    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE
    )
    """)

    # Expenses table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        category TEXT,
        amount REAL,
        note TEXT
    )
    """)

    conn.commit()
    conn.close()

create_tables()

# ---------------- User Functions ----------------
def get_or_create_user(email):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE email = ?", (email,))
    user = cur.fetchone()

    if user:
        user_id = user[0]
    else:
        cur.execute("INSERT INTO users (email) VALUES (?)", (email,))
        conn.commit()
        user_id = cur.lastrowid

    conn.close()
    return user_id

# ---------------- Expense Functions ----------------
def add_expense(user_id, date, category, amount, note):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (user_id, date, category, amount, note) VALUES (?, ?, ?, ?, ?)",
        (user_id, date, category, amount, note)
    )
    conn.commit()
    conn.close()

def get_user_expenses(user_id):
    conn = get_conn()
    df = pd.read_sql(
        "SELECT * FROM expenses WHERE user_id = ?",
        conn,
        params=(user_id,)
    )
    conn.close()
    return df

# ---------------- LOGIN ----------------
st.sidebar.header("🔐 Login")

email = st.sidebar.text_input("Enter your email")

if not email:
    st.warning("Please login to continue")
    st.stop()

user_id = get_or_create_user(email)
st.sidebar.success(f"Logged in as {email}")

# ---------------- Add Expense ----------------
st.header("➕ Add Expense")

with st.form("add_expense"):
    date = st.date_input("Date", datetime.date.today())
    category = st.selectbox(
        "Category",
        ["Food", "Travel", "Rent", "Shopping", "Other"]
    )
    amount = st.number_input("Amount", min_value=0.0, step=1.0)
    note = st.text_input("Note (optional)")
    submit = st.form_submit_button("Add Expense")

if submit:
    if amount <= 0:
        st.error("Amount must be greater than 0")
    else:
        add_expense(user_id, str(date), category, amount, note)
        st.success("Expense added")

# ---------------- Show Expenses ----------------
st.header("📊 Your Expenses")

df = get_user_expenses(user_id)

if df.empty:
    st.info("No expenses found")
else:
    df["date"] = pd.to_datetime(df["date"])
    st.dataframe(df.sort_values("date", ascending=False), use_container_width=True)

    # ---------------- Summary ----------------
    st.subheader("📌 Summary")

    total = df["amount"].sum()
    avg_exp = np.mean(df["amount"])
    max_exp = np.max(df["amount"])

    current_month = pd.Timestamp.today().to_period("M")
    monthly_total = df[df["date"].dt.to_period("M") == current_month]["amount"].sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total", f"₹{total:.2f}")
    col2.metric("Average", f"₹{avg_exp:.2f}")
    col3.metric("Highest", f"₹{max_exp:.2f}")
    col4.metric("This Month", f"₹{monthly_total:.2f}")

    # ---------------- Charts ----------------
    st.subheader("📂 Category-wise Spending")

    by_cat = df.groupby("category")["amount"].sum()
    fig1, ax1 = plt.subplots()
    by_cat.plot(kind="bar", ax=ax1)
    ax1.set_ylabel("Amount")
    st.pyplot(fig1)

    st.subheader("📈 Monthly Trend")

    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    monthly = df.groupby("month")["amount"].sum()

    fig2, ax2 = plt.subplots()
    ax2.plot(monthly.index, monthly.values, marker="o")
    ax2.set_ylabel("Amount")
    st.pyplot(fig2)
