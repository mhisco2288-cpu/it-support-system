import streamlit as st
import pandas as pd
import sqlite3
import requests
import time
import asyncio
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
from streamlit_lottie import st_lottie
from streamlit_option_menu import option_menu

# --- 1. إعدادات الصفحة ---
st.set_page_config(
    page_title="IT Command Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 🔴🔴🔴 هام جداً: ضع التوكين الخاص بك هنا بين علامتي التنصيص 🔴🔴🔴
TOKEN = "8560214645:AAFxskBVliT-KF5RJcNwCA2GNAv3Pqsgizw" 

# --- 2. إعداد قاعدة البيانات (لضمان عملها في السحابة) ---
def init_db():
    conn = sqlite3.connect('tickets.db', check_same_thread=False)
    c = conn.cursor()
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

# تشغيل دالة الإنشاء فوراً
init_db()

# --- 3. برمجة البوت (Telegram Bot) ---
TYPE, LOCATION, PHONE, DESCRIPTION = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🖥️ حاسبة", callback_data='Hardware'), InlineKeyboardButton("🌐 شبكة", callback_data='Network')],
        [InlineKeyboardButton("🖨️ طابعة", callback_data='Printer'), InlineKeyboardButton("💾 برمجيات", callback_data='Software')]
    ]
    await update.message.reply_text("👋 أهلاً بك في الدعم الفني.\nاختر نوع العطل:", reply_markup=InlineKeyboardMarkup(keyboard))
    return TYPE

async def get_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['type'] = query.data
    await query.edit_message_text(f"تم اختيار: {query.data}\n📍 أين مكان المشكلة (القسم/الغرفة)؟")
    return LOCATION

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['location'] = update.message.text
    await update.message.reply_text("📞 رقم للتواصل (أو اكتب 'لا يوجد'):")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("📝 صف المشكلة باختصار:")
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    data = context.user_data
    
    try:
        conn = sqlite3.connect('tickets.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT INTO tickets (user_id, username, issue_type, location, phone, description) VALUES (?, ?, ?, ?, ?, ?)",
                  (user.id, user.first_name, data['type'], data['location'], data['phone'], update.message.text))
        conn.commit()
        ticket_id = c.lastrowid
        conn.close()
        await update.message.reply_text(f"✅ تم فتح التذكرة رقم #{ticket_id}\nجاري إبلاغ الفريق المختص.")
    except Exception as e:
        await update.message.reply_text("حدث خطأ تقني، حاول لاحقاً.")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء الطلب.")
    return ConversationHandler.END

# --- تشغيل البوت في الخلفية (Background Thread) ---
def run_bot_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TYPE: [CallbackQueryHandler(get_type)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_location)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(conv_handler)
    application.run_polling()

# هذا الكود يضمن تشغيل البوت مرة واحدة فقط عند فتح الموقع
@st.cache_resource
def start_bot_background():
    if not any(t.name == "BotThread" for t in threading.enumerate()):
        t = threading.Thread(target=run_bot_loop, name="BotThread", daemon=True)
        t.start()

start_bot_background()

# --- 4. واجهة الموقع (Dashboard UI) ---
def load_lottieurl(url):
    try:
        r = requests.get(url)
        if r.status_code != 200: return None
        return r.json()
    except: return None

def get_data():
    conn = sqlite3.connect('tickets.db', check_same_thread=False)
    df = pd.read_sql_query("SELECT * FROM tickets ORDER BY id DESC", conn)
    conn.close()
    return df

def update_status(ticket_id, new_status):
    conn = sqlite3.connect('tickets.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("UPDATE tickets SET status = ? WHERE id = ?", (new_status, ticket_id))
    conn.commit()
    conn.close()

def send_telegram_message(user_id, message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": user_id, "text": message}
    try: requests.post(url, json=payload); return True
    except: return False

# CSS للتصميم
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;500;700;900&display=swap');
    * { font-family: 'Tajawal', sans-serif; }
    .stApp { background: linear-gradient(135deg, #1e1e2f 0%, #252540 100%); }
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px; padding: 20px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    }
    label[data-testid="stMetricLabel"] { color: #a6a6c3 !important; }
    div[data-testid="stMetricValue"] { color: #fff !important; }
    div[data-testid="stExpander"] {
        border: none; background: rgba(30, 30, 47, 0.7); border-radius: 15px; margin-bottom: 15px;
    }
    .block-container { direction: rtl; }
</style>
""", unsafe_allow_html=True)

# القائمة العلوية
selected = option_menu(
    menu_title=None,
    options=["الرئيسية", "التذاكر النشطة", "الأرشيف"],
    icons=["speedometer2", "list-task", "archive"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={"nav-link-selected": {"background-color": "#00d2ff"}}
)

df = get_data()

if selected == "الرئيسية":
    c1, c2 = st.columns([2, 1])
    with c1: st.markdown("<h1 style='color: white;'>🚀 مركز القيادة</h1>", unsafe_allow_html=True)
    with c2:
        lottie = load_lottieurl("https://lottie.host/5a092797-3932-4cc7-b644-245842812260/p6S0j5Yg7t.json")
        if lottie: st_lottie(lottie, height=150, key="anim")
        else: st.write("📊")

    if not df.empty:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("الكل", len(df))
        k2.metric("جديد", len(df[df['status']=='جديد']))
        k3.metric("جاري", len(df[df['status']=='قيد العمل']))
        k4.metric("مغلق", len(df[df['status']=='مغلق']))
    else:
        st.info("النظام جاهز. أرسل رسالة للبوت للتجربة.")

elif selected == "التذاكر النشطة":
    st.markdown("### ⚡ المهام الحالية")
    if st.button("تحديث 🔄"): st.rerun()
    
    active_df = df[df['status'] != 'مغلق']
    if active_df.empty:
        st.success("لا توجد مهام نشطة")
    else:
        for i, row in active_df.iterrows():
            with st.expander(f"🎫 {row['issue_type']} | {row['username']}"):
                st.write(f"📝 {row['description']}")
                st.caption(f"📍 {row['location']} | 📞 {row['phone']}")
                
                c1, c2 = st.columns(2)
                with c1:
                    new_st = st.selectbox("الحالة", ["جديد", "قيد العمل", "مغلق"], key=f"s_{row['id']}")
                    if new_st != row['status']:
                        update_status(row['id'], new_st)
                        st.rerun()
                with c2:
                    rep = st.text_input("الرد:", key=f"r_{row['id']}")
                    if st.button("إرسال", key=f"b_{row['id']}"):
                        if send_telegram_message(row['user_id'], f"تحديث: {rep}"):
                            st.success("تم الإرسال")

elif selected == "الأرشيف":
    st.markdown("### 🗄️ الأرشيف")
    st.dataframe(df[df['status'] == 'مغلق'], use_container_width=True)

