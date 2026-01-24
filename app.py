import streamlit as st
import mysql.connector
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import smtplib
from email.message import EmailMessage
import os
import re

# ---------------- Page Config ----------------
st.set_page_config(
    page_title="Expense Tracker",
    page_icon="💰",
    layout="centered"
)

st.title("💰 Multi-User Expense Tracker")
st.caption("Track • Analyze • Control your expenses")

# ---------------- EMAIL CONFIG ----------------
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

def is_valid_email(email):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email)

def send_email_alert(to_email, total, budget):
    try:
        if not SENDGRID_API_KEY or not SENDER_EMAIL:
            return

        msg = EmailMessage()
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = "⚠ Budget Exceeded Alert"

        msg.set_content(f"""
Hello,

Your monthly expense has exceeded the set budget.

Budget: ₹{budget}
Total Expense: ₹{total}

Expense Tracker System
""")

        server = smtplib.SMTP("smtp.sendgrid.net", 587)
        server.starttls()
        server.login("apikey", SENDGRID_API_KEY)
        server.send_message(msg)
        server.quit()
    except:
        pass   # free hosting me email fail ho sakta hai

# ---------------- DATABASE ----------------
def get_conn():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306))
    )

# ---------------- USER ----------------
def get_or_create_user(email):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email=%s", (email,))
    row = cur.fetchone()

    if row:
        uid = row[0]
    else:
        cur.execute("INSERT INTO users (email) VALUES (%s)", (email,))
        conn.commit()
        uid = cur.lastrowid

    conn.close()
    return uid

def get_user_budget(uid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT budget FROM users WHERE id=%s", (uid,))
    row = cur.fetchone()
    conn.close()
    return row[0]

def set_user_budget(uid, budget):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET budget=%s, alert_sent=0 WHERE id=%s", (budget, uid))
    conn.commit()
    conn.close()

def is_alert_sent(uid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT alert_sent FROM users WHERE id=%s", (uid,))
    sent = cur.fetchone()[0]
    conn.close()
    return sent == 1

def mark_alert_sent(uid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET alert_sent=1 WHERE id=%s", (uid,))
    conn.commit()
    conn.close()

# ---------------- EXPENSE ----------------
def add_expense(uid, date, category, amount, note):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (user_id, date, category, amount, note) VALUES (%s,%s,%s,%s,%s)",
        (uid, date, category, amount, note)
    )
    conn.commit()
    conn.close()

def get_expenses(uid):
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM expenses WHERE user_id=%s", conn, params=(uid,))
    conn.close()
    return df

# ---------------- LOGIN ----------------
if "user_email" not in st.session_state:
    st.session_state.user_email = st.query_params.get("user", "")

st.sidebar.header("🔐 Login")
email_input = st.sidebar.text_input("Email")

if st.sidebar.button("Login"):
    if not is_valid_email(email_input):
        st.sidebar.error("Please enter a valid email address")
    else:
        st.session_state.user_email = email_input
        st.query_params["user"] = email_input
        st.rerun()

if not st.session_state.user_email:
    st.stop()

uid = get_or_create_user(st.session_state.user_email)
st.sidebar.success(st.session_state.user_email)

# ---------------- ADD EXPENSE ----------------
st.header("➕ Add Expense")

with st.form("add_expense"):
    c1, c2 = st.columns(2)
    with c1:
        date = st.date_input("Date", datetime.date.today())
        category = st.selectbox("Category", ["Food", "Travel", "Rent", "Shopping", "Other"])
    with c2:
        amount = st.number_input("Amount", min_value=0.0)
        note = st.text_input("Note")
    submit = st.form_submit_button("Add")

if submit and amount > 0:
    add_expense(uid, str(date), category, amount, note)
    st.success("Expense added")
    st.rerun()

# ---------------- CSV UPLOAD (BEFORE BUDGET) ----------------
st.header("📥 Upload CSV")
csv = st.file_uploader("Upload CSV (date,category,amount,note)", type=["csv"])

if csv:
    df_csv = pd.read_csv(csv)
    for _, r in df_csv.iterrows():
        add_expense(uid, r["date"], r["category"], r["amount"], r.get("note", ""))
    st.success("CSV uploaded successfully")
    st.rerun()

# ---------------- LOAD DATA ----------------
df = get_expenses(uid)
if df.empty:
    st.warning("No expenses yet")
    st.stop()

df["date"] = pd.to_datetime(df["date"])

# ---------------- FILTER DATA ----------------
st.header("🔎 Filter Expenses")
col1, col2 = st.columns(2)

with col1:
    f_category = st.selectbox("Category", ["All"] + sorted(df["category"].unique()))
with col2:
    f_month = st.selectbox(
        "Month",
        ["All"] + sorted(df["date"].dt.strftime("%Y-%m").unique())
    )

filtered_df = df.copy()

if f_category != "All":
    filtered_df = filtered_df[filtered_df["category"] == f_category]

if f_month != "All":
    filtered_df = filtered_df[filtered_df["date"].dt.strftime("%Y-%m") == f_month]

# ---------------- BUDGET ----------------
st.header("💡 Monthly Budget")
saved_budget = get_user_budget(uid)
budget = st.number_input("Set Budget", value=int(saved_budget) if saved_budget else 0)

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

# ---------------- SUMMARY ----------------
st.header("📊 Summary")
c1, c2, c3 = st.columns(3)
c1.metric("Total", f"₹{filtered_df['amount'].sum():.0f}")
c2.metric("Average", f"₹{filtered_df['amount'].mean():.0f}")
c3.metric("Highest", f"₹{filtered_df['amount'].max():.0f}")

# ---------------- CHARTS ----------------
st.header("📈 Charts")

# Pie
pie = filtered_df.groupby("category")["amount"].sum()
fig1, ax1 = plt.subplots()
ax1.pie(pie, labels=pie.index, autopct="%1.1f%%")
st.pyplot(fig1)

# Bar
fig2, ax2 = plt.subplots()
ax2.bar(pie.index, pie.values)
st.pyplot(fig2)

# Monthly Line
filtered_df["month"] = filtered_df["date"].dt.to_period("M").dt.to_timestamp()
trend = filtered_df.groupby("month")["amount"].sum()
fig3, ax3 = plt.subplots()
ax3.plot(trend.index, trend.values, marker="o")
st.pyplot(fig3)

# ---------------- DOWNLOAD ----------------
st.header("⬇ Download")
st.download_button(
    "Download Filtered CSV",
    filtered_df.to_csv(index=False),
    "expenses.csv"
)
