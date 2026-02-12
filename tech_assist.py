import streamlit as st
import pandas as pd
import sqlite3
import requests
import time
import asyncio
import threading
import nest_asyncio
import plotly.express as px
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
from streamlit_option_menu import option_menu

# --- 1. إعدادات النظام ---
nest_asyncio.apply()
st.set_page_config(page_title="TechAssist", page_icon="🛠️", layout="wide")

# 🔴🔴🔴 ضع التوكين هنا 🔴🔴🔴
TOKEN = "7690158561:AAH9kiOjUNZIErzlWUtYdAzOThRGRLoBkLc" 

# تصميم نظيف وبسيط (Clean UI)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;500;800&display=swap');
    * { font-family: 'Tajawal', sans-serif; }
    .stApp { background-color: #f0f2f6; }
    div[data-testid="metric-container"] { background-color: white; border-radius: 10px; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    div[data-testid="stDataFrame"] { background-color: white; padding: 10px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. قاعدة البيانات (ملف جديد) ---
def init_db():
    # سنستخدم اسماً جديداً لقاعدة البيانات لتجنب أي تضارب قديم
    conn = sqlite3.connect('tech_assist.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS support_tickets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ticket_ref TEXT,
                  user_id INTEGER,
                  username TEXT,
                  category TEXT,
                  details TEXT,
                  location TEXT,
                  phone TEXT,
                  status TEXT DEFAULT 'جديد',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- 3. البوت (Telegram Logic) ---
CAT, DETAIL, LOC, PHONE = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **مرحباً بك في TechAssist**\n\nلفتح تذكرة دعم فني، يرجى اختيار القسم:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💻 حاسب آلي", callback_data='Computer'), InlineKeyboardButton("🌐 شبكات", callback_data='Network')],
            [InlineKeyboardButton("🖨️ طابعات", callback_data='Printer'), InlineKeyboardButton("🔑 أخرى", callback_data='Other')]
        ])
    )
    return CAT

async def get_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['cat'] = query.data
    await query.edit_message_text(f"القسم: {query.data}\n📝 صف المشكلة بالتفصيل:")
    return DETAIL

async def get_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['detail'] = update.message.text
    await update.message.reply_text("📍 الموقع (المكتب/الغرفة):")
    return LOC

async def get_loc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['loc'] = update.message.text
    await update.message.reply_text("📞 رقم جوال للتواصل:")
    return PHONE

async def save_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    user = update.message.from_user
    data = context.user_data
    ref = f"TIC-{int(time.time())}"
    
    conn = sqlite3.connect('tech_assist.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO support_tickets (ticket_ref, user_id, username, category, details, location, phone) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (ref, user.id, user.first_name, data['cat'], data['detail'], data['loc'], phone))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"✅ تم رفع الطلب بنجاح!\nرقم التذكرة: `{ref}`")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم الإلغاء.")
    return ConversationHandler.END

# تشغيل البوت في الخلفية (Threading)
def run_bot_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = Application.builder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CAT: [CallbackQueryHandler(get_cat)],
            DETAIL: [MessageHandler(filters.TEXT, get_detail)],
            LOC: [MessageHandler(filters.TEXT, get_loc)],
            PHONE: [MessageHandler(filters.TEXT, save_data)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    app.add_handler(conv)
    
    try:
        loop.run_until_complete(app.bot.delete_webhook(drop_pending_updates=True))
    except:
        pass
        
    app.run_polling()

# منع التشغيل المزدوج
if not any(t.name == "TechAssistBot" for t in threading.enumerate()):
    t = threading.Thread(target=run_bot_thread, name="TechAssistBot", daemon=True)
    t.start()

# --- 4. واجهة الموقع ---
with st.sidebar:
    st.title("🛠️ TechAssist")
    page = option_menu("القائمة", ["نظرة عامة", "التذاكر", "الأرشيف"], icons=['speedometer2', 'ticket-perforated', 'archive'])

def get_tickets():
    conn = sqlite3.connect('tech_assist.db')
    df = pd.read_sql_query("SELECT * FROM support_tickets ORDER BY id DESC", conn)
    conn.close()
    return df

if page == "نظرة عامة":
    st.header("📊 لوحة المعلومات")
    df = get_tickets()
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي التذاكر", len(df))
        c2.metric("تذاكر مفتوحة", len(df[df['status']=='جديد']))
        c3.metric("مكتملة", len(df[df['status']=='مكتمل']))
        
        st.markdown("---")
        fig = px.bar(df, x='category', title="توزيع التذاكر حسب القسم", color='status')
        st.plotly_chart(fig, use_container_width=True)

elif page == "التذاكر":
    st.header("🎫 التذاكر النشطة")
    if st.button("تحديث البيانات 🔄"): st.rerun()
    
    df = get_tickets()
    active = df[df['status'] == 'جديد']
    
    if active.empty:
        st.success("لا توجد مهام جديدة.")
    else:
        for i, row in active.iterrows():
            with st.expander(f"🔴 {row['category']} | {row['username']} ({row['ticket_ref']})"):
                st.write(f"**المشكلة:** {row['details']}")
                st.write(f"**الموقع:** {row['location']} | **هاتف:** {row['phone']}")
                
                if st.button("إغلاق التذكرة ✅", key=f"close_{row['id']}"):
                    conn = sqlite3.connect('tech_assist.db')
                    conn.execute("UPDATE support_tickets SET status='مكتمل' WHERE id=?", (row['id'],))
                    conn.commit()
                    conn.close()
                    st.success("تم إغلاق التذكرة!")
                    time.sleep(1)
                    st.rerun()

elif page == "الأرشيف":
    st.header("🗄️ سجل التذاكر")
    df = get_tickets()
    st.dataframe(df, use_container_width=True)
