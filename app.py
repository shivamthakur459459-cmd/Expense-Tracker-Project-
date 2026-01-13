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

# ---------------- EMAIL CONFIG ----------------
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")


def send_email_alert(to_email, total, budget):
    msg = EmailMessage()
    msg["Subject"] = "⚠ Expense Budget Alert"
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email

    msg.set_content(f"""
Hello,

Your monthly expense has crossed the budget limit.

Budget: ₹{budget}
Total Expense: ₹{total}

Please check your Expense Tracker application.

Thank you
""")

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(SENDER_EMAIL, APP_PASSWORD)
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
        email TEXT UNIQUE
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

# ---------------- Expense CRUD ----------------
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
    df = pd.read_sql(
        "SELECT * FROM expenses WHERE user_id=?",
        conn,
        params=(uid,)
    )
    conn.close()
    return df

def delete_expense(exp_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id=?", (exp_id,))
    conn.commit()
    conn.close()

def update_expense(exp_id, date, cat, amt, note):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE expenses
        SET date=?, category=?, amount=?, note=?
        WHERE id=?
    """, (date, cat, amt, note, exp_id))
    conn.commit()
    conn.close()

# ---------------- Sidebar Login ----------------
st.sidebar.header("🔐 Login")

if "user_email" not in st.session_state:
    st.session_state.user_email = None

email = st.sidebar.text_input("Email")

if st.sidebar.button("Login"):
    if email:
        st.session_state.user_email = email

if st.session_state.user_email is None:
    st.info("Please login to continue")
    st.stop()

uid = get_or_create_user(st.session_state.user_email)
st.sidebar.success(st.session_state.user_email)

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ---------------- Add Expense ----------------
st.header("➕ Add Expense")

with st.form("add"):
    c1, c2 = st.columns(2)
    with c1:
        date = st.date_input("Date", datetime.date.today())
        category = st.selectbox("Category", ["Food","Travel","Rent","Shopping","Other"])
    with c2:
        amount = st.number_input("Amount", min_value=0.0, step=1.0)
        note = st.text_input("Note")
    submit = st.form_submit_button("Add")

if submit and amount > 0:
    add_expense(uid, str(date), category, amount, note)
    st.success("Expense added")
    st.rerun()

# ---------------- Load Data ----------------
df = get_expenses(uid)
if df.empty:
    st.warning("No data found")
    st.stop()

df["date"] = pd.to_datetime(df["date"])

# ---------------- Filters ----------------
st.header("🔍 Filters")
c1, c2 = st.columns(2)
with c1:
    start = st.date_input("Start", df["date"].min().date())
with c2:
    end = st.date_input("End", df["date"].max().date())

cat = st.selectbox("Category", ["All"] + sorted(df["category"].unique()))
fdf = df[(df["date"]>=pd.to_datetime(start)) & (df["date"]<=pd.to_datetime(end))]
if cat!="All":
    fdf = fdf[fdf["category"]==cat]

# ---------------- Budget + EMAIL ALERT ----------------
st.header("💡 Monthly Budget")
budget = st.number_input("Set budget", value=5000)

current_month = pd.Timestamp.today().to_period("M")
month_total = fdf[fdf["date"].dt.to_period("M")==current_month]["amount"].sum()

if "alert_sent" not in st.session_state:
    st.session_state.alert_sent = False

if month_total > budget:
    st.error("⚠ Budget exceeded")

    if not st.session_state.alert_sent:
        send_email_alert(st.session_state.user_email, month_total, budget)
        st.session_state.alert_sent = True
        st.success("📧 Budget alert email sent")
else:
    st.success("Budget under control")
    st.session_state.alert_sent = False

# ---------------- Summary ----------------
st.header("📊 Summary")
c1,c2,c3 = st.columns(3)
c1.metric("Total", f"₹{fdf['amount'].sum():.0f}")
c2.metric("Average", f"₹{fdf['amount'].mean():.0f}")
c3.metric("Highest", f"₹{fdf['amount'].max():.0f}")

# ---------------- Edit / Delete ----------------
st.header("✏ Edit / Delete Expenses")

for _, r in fdf.iterrows():
    with st.expander(f"{r['date'].date()} | {r['category']} | ₹{r['amount']}"):
        nd = st.date_input("Date", r["date"].date(), key=f"d{r['id']}")
        nc = st.selectbox("Category", ["Food","Travel","Rent","Shopping","Other"],
                          index=["Food","Travel","Rent","Shopping","Other"].index(r["category"]),
                          key=f"c{r['id']}")
        na = st.number_input("Amount", value=float(r["amount"]), key=f"a{r['id']}")
        nn = st.text_input("Note", r["note"], key=f"n{r['id']}")

        col1,col2 = st.columns(2)
        if col1.button("Update", key=f"u{r['id']}"):
            update_expense(r["id"], str(nd), nc, na, nn)
            st.rerun()

        if col2.button("Delete", key=f"x{r['id']}"):
            delete_expense(r["id"])
            st.rerun()

# ---------------- Charts ----------------
st.header("📈 Charts")

pie = fdf.groupby("category")["amount"].sum()
fig1,ax1 = plt.subplots()
ax1.pie(pie, labels=pie.index, autopct="%1.1f%%")
st.pyplot(fig1)

fdf["month"] = fdf["date"].dt.to_period("M").dt.to_timestamp()
trend = fdf.groupby("month")["amount"].sum()
fig2,ax2 = plt.subplots()
ax2.plot(trend.index, trend.values, marker="o")
st.pyplot(fig2)

# ---------------- Download ----------------
st.header("⬇ Download")

def to_excel(df):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return buf.getvalue()

st.download_button("Download CSV", fdf.to_csv(index=False), "expenses.csv")
st.download_button("Download Excel", to_excel(fdf), "expenses.xlsx")
