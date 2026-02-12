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
    initial_sidebar_state="collapsed"  # سنخفي القائمة الجانبية لجمالية أكثر
)

# --- 2. المتغيرات والاتصال ---
# 🔴🔴🔴 ضع التوكين هنا 🔴🔴🔴
TOKEN = "8560214645:AAFxskBVliT-KF5RJcNwCA2GNAv3Pqsgizw" 

# روابط الانيميشن
LOTTIE_DASHBOARD = "https://lottie.host/5a092797-3932-4cc7-b644-245842812260/p6S0j5Yg7t.json"
LOTTIE_LOADING = "https://assets9.lottiefiles.com/packages/lf20_p8bfn5to.json"

# --- 3. تصميم CSS الخرافي (Glassmorphism) ---
st.markdown("""
<style>
    /* استيراد خط تجوال العصري */
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;500;700;900&display=swap');

    * { font-family: 'Tajawal', sans-serif; }

    /* خلفية متدرجة احترافية */
    .stApp {
        background: linear-gradient(135deg, #1e1e2f 0%, #252540 100%);
    }

    /* كروت الإحصائيات (Metrics) */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        transition: transform 0.2s;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        border-color: #00d2ff;
    }
    label[data-testid="stMetricLabel"] { color: #a6a6c3 !important; font-size: 1.1rem !important; }
    div[data-testid="stMetricValue"] { color: #fff !important; font-size: 2.5rem !important; text-shadow: 0 0 10px rgba(0,210,255,0.5); }

    /* تحسين البطاقات (Expanders) */
    .streamlit-expanderHeader {
        background-color: rgba(255, 255, 255, 0.03) !important;
        border-radius: 10px !important;
        color: white !important;
        font-weight: bold;
    }
    
    div[data-testid="stExpander"] {
        border: none;
        background: rgba(30, 30, 47, 0.7);
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        margin-bottom: 15px;
        border-right: 5px solid #444; /* Default border */
    }

    /* أزرار ملونة */
    div.stButton > button {
        background: linear-gradient(90deg, #00d2ff 0%, #3a7bd5 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        box-shadow: 0 0 15px #00d2ff;
        transform: scale(1.02);
    }
    
    /* جعل النصوص تظهر من اليمين لليسار */
    .block-container { direction: rtl; }
    
</style>
""", unsafe_allow_html=True)

# --- 4. الدوال المساعدة ---
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

# --- 5. الهيكل الرئيسي للواجهة ---

# شريط التنقل العلوي (حديث جداً)
selected = option_menu(
    menu_title=None,
    options=["الرئيسية", "التذاكر النشطة", "الأرشيف", "إعدادات"],
    icons=["speedometer2", "list-task", "archive", "gear"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "transparent"},
        "icon": {"color": "#00d2ff", "font-size": "18px"}, 
        "nav-link": {"font-size": "16px", "text-align": "center", "margin": "0px", "--hover-color": "#2c2c42"},
        "nav-link-selected": {"background-color": "#252540", "border-bottom": "3px solid #00d2ff"},
    }
)

df = get_data()

# ================= صفحة الرئيسية (Dashboard) =================
if selected == "الرئيسية":
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("<h1 style='color: white;'>🚀 مركز القيادة الرقمي</h1>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: #a6a6c3;'>مرحباً بك في الجيل الجديد من إدارة الدعم الفني.</h4>", unsafe_allow_html=True)
    with col2:
        lottie_dash = load_lottieurl(LOTTIE_DASHBOARD)
        st_lottie(lottie_dash, height=150, key="dash_anim")

    st.markdown("---")

    # بطاقات الإحصائيات المضيئة (KPIs)
    if not df.empty:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("إجمالي الطلبات", len(df), "+2 اليوم")
        k2.metric("🔴 تذاكر جديدة", len(df[df['status'] == 'جديد']), "حرج", delta_color="inverse")
        k3.metric("🟡 قيد العمل", len(df[df['status'] == 'قيد العمل']))
        k4.metric("✅ المكتملة", len(df[df['status'] == 'مغلق']))
    
    # رسوم بيانية سريعة (تحتاج دالة بسيطة)
    st.markdown("### 📊 تحليل الأداء السريع")
    c1, c2 = st.columns(2)
    with c1:
        if not df.empty:
            st.bar_chart(df['issue_type'].value_counts())
            st.caption("توزيع المشاكل حسب النوع")
    with c2:
         if not df.empty:
            st.line_chart(df['created_at'].value_counts()) # مجرد مثال، يحتاج معالجة تواريخ ليكون دقيقاً
            st.caption("نشاط التذاكر عبر الزمن")

# ================= صفحة التذاكر النشطة =================
elif selected == "التذاكر النشطة":
    st.markdown("<h2 style='text-align: center; color: #00d2ff;'>⚡ قائمة المهام الحالية</h2>", unsafe_allow_html=True)
    
    # فلتر سريع
    col_filter, col_refresh = st.columns([4, 1])
    with col_refresh:
        if st.button("تحديث 🔄"): st.rerun()
    
    active_df = df[df['status'] != 'مغلق']
    
    if active_df.empty:
        st.success("🎉 لا توجد مهام! استمتع بوقتك.")
    else:
        for i, row in active_df.iterrows():
            # تحديد لون الجانب حسب الحالة
            status_color = "#ff4b4b" if row['status'] == 'جديد' else "#ffa421"
            
            # حقن CSS خاص لكل بطاقة لتلوين الحافة
            st.markdown(f"""
            <style>
            div[data-testid="stExpander"]:nth-child({i+2}) {{
                border-right: 5px solid {status_color} !important;
            }}
            </style>
            """, unsafe_allow_html=True)

            with st.expander(f"🎫 تذكرة #{row['id']} | {row['issue_type']} | {row['username']}"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown(f"#### 📝 {row['description']}")
                    st.markdown(f"**📍 الموقع:** `{row['location']}`  |  **📞 هاتف:** `{row['phone']}`")
                    st.caption(f"🕒 {row['created_at']}")
                
                with c2:
                    st.markdown("##### ⚙️ الإجراءات")
                    new_st = st.selectbox("تحديث الحالة", ["جديد", "قيد العمل", "مغلق"], key=f"s_{row['id']}", label_visibility="collapsed")
                    if new_st != row['status']:
                        update_status(row['id'], new_st)
                        st.rerun()
                    
                    rep = st.text_input("الرد السريع", placeholder="اكتب ردك...", key=f"r_{row['id']}", label_visibility="collapsed")
                    if st.button("إرسال الرد 🚀", key=f"b_{row['id']}"):
                        if send_telegram_message(row['user_id'], f"تحديث: {rep}"): st.toast("تم الإرسال!", icon="✅")

# ================= صفحة الأرشيف =================
elif selected == "الأرشيف":
    st.markdown("### 🗄️ سجل العمليات السابق")
    closed_df = df[df['status'] == 'مغلق']
    st.dataframe(closed_df, use_container_width=True)

# ================= صفحة الإعدادات (شكلية) =================
elif selected == "إعدادات":
    st.info("هنا يمكن إضافة إعدادات لإضافة موظفين جدد أو تغيير التنبيهات مستقبلاً.")

