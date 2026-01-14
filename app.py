import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import smtplib
from email.message import EmailMessage
from io import BytesIO
import os

# ---------------- Page Config ----------------
st.set_page_config(
    page_title="Expense Tracker",
    page_icon="💰",
    layout="centered"
)

st.title("💰 Multi-User Expense Tracker")
st.caption("Track • Analyze • Control your expenses")

DB_NAME = "expenses.db"

# ---------------- EMAIL (SendGrid SMTP) ----------------
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

def send_email_alert(to_email, total, budget):
    if not SENDGRID_API_KEY or not SENDER_EMAIL:
        return

    msg = EmailMessage()
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = "⚠ Expense Budget Alert"

    msg.set_content(f"""
Hello,

Your monthly expense has crossed your budget.

Budget: ₹{budget}
Total Expense: ₹{total}

Expense Tracker System
""")

    server = smtplib.SMTP("smtp.sendgrid.net", 587)
    server.starttls()
    server.login("apikey", SENDGRID_API_KEY)
    server.send_message(msg)
    server.quit()

# ---------------- Database ----------------
def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        budget REAL DEFAULT NULL,
        alert_sent INTEGER DEFAULT 0
    )
    """)

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

init_db()

# ---------------- User ----------------
def get_or_create_user(email):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email=?", (email,))
    row = cur.fetchone()

    if row:
        uid = row[0]
    else:
        cur.execute("INSERT INTO users (email) VALUES (?)", (email,))
        conn.commit()
        uid = cur.lastrowid

    conn.close()
    return uid

def get_user_budget(uid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT budget FROM users WHERE id=?", (uid,))
    row = cur.fetchone()
    conn.close()
    return row[0]

def set_user_budget(uid, budget):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET budget=?, alert_sent=0 WHERE id=?", (budget, uid))
    conn.commit()
    conn.close()

def is_alert_sent(uid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT alert_sent FROM users WHERE id=?", (uid,))
    sent = cur.fetchone()[0]
    conn.close()
    return sent == 1

def mark_alert_sent(uid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET alert_sent=1 WHERE id=?", (uid,))
    conn.commit()
    conn.close()

# ---------------- Expenses ----------------
def add_expense(uid, date, cat, amt, note):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (user_id,date,category,amount,note) VALUES (?,?,?,?,?)",
        (uid, date, cat, amt, note)
    )
    conn.commit()
    conn.close()

def get_expenses(uid):
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM expenses WHERE user_id=?", conn, params=(uid,))
    conn.close()
    return df

# ---------------- Session Login (NO LOGOUT ON REFRESH) ----------------
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

st.sidebar.header("🔐 Login")
email_input = st.sidebar.text_input("Email", st.session_state.user_email)

if st.sidebar.button("Login"):
    if email_input:
        st.session_state.user_email = email_input

if not st.session_state.user_email:
    st.info("Please login")
    st.stop()

uid = get_or_create_user(st.session_state.user_email)
st.sidebar.success(st.session_state.user_email)

# ---------------- Add Expense ----------------
st.header("➕ Add Expense")

with st.form("add_expense"):
    c1, c2 = st.columns(2)
    with c1:
        date = st.date_input("Date", datetime.date.today())
        category = st.selectbox("Category", ["Food","Travel","Rent","Shopping","Other"])
    with c2:
        amount = st.number_input("Amount", min_value=0.0)
        note = st.text_input("Note")
    submit = st.form_submit_button("Add")

if submit and amount > 0:
    add_expense(uid, str(date), category, amount, note)
    st.success("Expense added")
    st.rerun()

# ---------------- CSV Upload ----------------
st.header("📥 Upload CSV")
csv = st.file_uploader("Upload CSV (date,category,amount,note)", type=["csv"])

if csv:
    df_csv = pd.read_csv(csv)
    for _, r in df_csv.iterrows():
        add_expense(uid, r["date"], r["category"], r["amount"], r.get("note",""))
    st.success("CSV uploaded")
    st.rerun()

# ---------------- Load Data ----------------
df = get_expenses(uid)
if df.empty:
    st.warning("No expenses yet")
    st.stop()

df["date"] = pd.to_datetime(df["date"])

# ---------------- Budget ----------------
st.header("💡 Monthly Budget")

saved_budget = get_user_budget(uid)
budget = st.number_input(
    "Set Budget",
    value=int(saved_budget) if saved_budget else 0
)

if st.button("Save Budget"):
    set_user_budget(uid, budget)
    st.success("Budget saved")

current_month = pd.Timestamp.today().to_period("M")
month_total = df[df["date"].dt.to_period("M") == current_month]["amount"].sum()

if budget and month_total > budget:
    st.error("⚠ Budget exceeded")

    if not is_alert_sent(uid):
        send_email_alert(st.session_state.user_email, month_total, budget)
        mark_alert_sent(uid)
        st.success("📧 Alert email sent")
else:
    st.success("Budget under control")

# ---------------- Summary ----------------
st.header("📊 Summary")
c1, c2, c3 = st.columns(3)
c1.metric("Total", f"₹{df['amount'].sum():.0f}")
c2.metric("Average", f"₹{df['amount'].mean():.0f}")
c3.metric("Highest", f"₹{df['amount'].max():.0f}")

# ---------------- Charts ----------------
st.header("📈 Charts")

pie = df.groupby("category")["amount"].sum()
fig1, ax1 = plt.subplots()
ax1.pie(pie, labels=pie.index, autopct="%1.1f%%")
st.pyplot(fig1)

df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
trend = df.groupby("month")["amount"].sum()
fig2, ax2 = plt.subplots()
ax2.plot(trend.index, trend.values, marker="o")
st.pyplot(fig2)

# ---------------- Download ----------------
st.header("⬇ Download")

st.download_button(
    "Download CSV",
    df.to_csv(index=False),
    "expenses.csv"
)
