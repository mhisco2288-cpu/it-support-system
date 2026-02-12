import streamlit as st
import pandas as pd
import sqlite3
import requests
import time
from streamlit_lottie import st_lottie
from streamlit_option_menu import option_menu

# --- 1. إعدادات الصفحة ---
st.set_page_config(
    page_title="IT Command Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 🔴🔴🔴 ضع التوكين الخاص بك هنا 🔴🔴🔴
TOKEN = "8560214645:AAFxskBVliT-KF5RJcNwCA2GNAv3Pqsgizw" 

# --- 2. إنشاء قاعدة البيانات (الحل للمشكلة الحالية) ---
# هذه الدالة تتأكد من وجود الجدول قبل أي شيء آخر
def init_db():
    conn = sqlite3.connect('tickets.db')
    c = conn.cursor()
    # إنشاء الجدول إذا لم يكن موجوداً
    c.execute('''CREATE TABLE IF NOT EXISTS tickets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  username TEXT,
                  issue_type TEXT,
                  location TEXT,
                  phone TEXT,
                  description TEXT,
                  status TEXT DEFAULT 'جديد',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# 🔥 تشغيل دالة الإنشاء فوراً 🔥
init_db()

# --- 3. الدوال المساعدة ---
# دالة آمنة لتحميل الأنيميشن (تمنع الشاشة الحمراء)
def load_lottieurl(url):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

def get_data():
    conn = sqlite3.connect('tickets.db')
    # الآن هذا السطر آمن لأن الجدول تم إنشاؤه في الأعلى
    df = pd.read_sql_query("SELECT * FROM tickets ORDER BY id DESC", conn)
    conn.close()
    return df

def update_status(ticket_id, new_status):
    conn = sqlite3.connect('tickets.db')
    c = conn.cursor()
    c.execute("UPDATE tickets SET status = ? WHERE id = ?", (new_status, ticket_id))
    conn.commit()
    conn.close()

def send_telegram_message(user_id, message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": user_id, "text": message}
    try: requests.post(url, json=payload); return True
    except: return False

# روابط الانيميشن
LOTTIE_DASHBOARD = "https://lottie.host/5a092797-3932-4cc7-b644-245842812260/p6S0j5Yg7t.json"

# --- 4. تصميم CSS (Glassmorphism) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;500;700;900&display=swap');
    * { font-family: 'Tajawal', sans-serif; }
    .stApp { background: linear-gradient(135deg, #1e1e2f 0%, #252540 100%); }
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    }
    label[data-testid="stMetricLabel"] { color: #a6a6c3 !important; }
    div[data-testid="stMetricValue"] { color: #fff !important; }
    div[data-testid="stExpander"] {
        border: none;
        background: rgba(30, 30, 47, 0.7);
        border-radius: 15px;
        margin-bottom: 15px;
    }
    .block-container { direction: rtl; }
</style>
""", unsafe_allow_html=True)

# --- 5. الواجهة الرئيسية ---
selected = option_menu(
    menu_title=None,
    options=["الرئيسية", "التذاكر النشطة", "الأرشيف"],
    icons=["speedometer2", "list-task", "archive"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={"nav-link-selected": {"background-color": "#00d2ff"}}
)

# جلب البيانات (لن يحدث خطأ الآن)
df = get_data()

if selected == "الرئيسية":
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("<h1 style='color: white;'>🚀 مركز القيادة الرقمي</h1>", unsafe_allow_html=True)
    with col2:
        # تحميل الأنيميشن بشكل آمن
        lottie_json = load_lottieurl(LOTTIE_DASHBOARD)
        if lottie_json:
            st_lottie(lottie_json, height=150, key="dash")
        else:
            st.write("📊")

    if not df.empty:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("الكل", len(df))
        k2.metric("جديد", len(df[df['status'] == 'جديد']))
        k3.metric("قيد العمل", len(df[df['status'] == 'قيد العمل']))
        k4.metric("مغلق", len(df[df['status'] == 'مغلق']))
    else:
        st.info("لا توجد بيانات حالياً - قاعدة البيانات جديدة")

elif selected == "التذاكر النشطة":
    st.markdown("### ⚡ التذاكر النشطة")
    if st.button("تحديث 🔄"): st.rerun()
    
    active_df = df[df['status'] != 'مغلق']
    if active_df.empty:
        st.success("لا توجد تذاكر نشطة")
    else:
        for i, row in active_df.iterrows():
            with st.expander(f"🎫 {row['issue_type']} | {row['username']}"):
                st.write(f"**الوصف:** {row['description']}")
                st.write(f"**الموقع:** {row['location']} - {row['phone']}")
                
                new_st = st.selectbox("الحالة", ["جديد", "قيد العمل", "مغلق"], key=f"s_{row['id']}")
                if new_st != row['status']:
                    update_status(row['id'], new_st)
                    st.rerun()

elif selected == "الأرشيف":
    st.markdown("### 🗄️ الأرشيف")
    st.dataframe(df[df['status'] == 'مغلق'], use_container_width=True)

