import streamlit as st
import pandas as pd
import sqlite3
import requests
import time
import asyncio
import threading
import nest_asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
from streamlit_lottie import st_lottie
from streamlit_option_menu import option_menu

# تطبيق إصلاح الحلقات (ضروري جداً للسحابة)
nest_asyncio.apply()

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="IT Center", page_icon="🔧", layout="wide", initial_sidebar_state="collapsed")

# 🔴🔴🔴 ضع التوكين الجديد هنا 🔴🔴🔴
TOKEN = "7690158561:AAH9kiOjUNZIErzlWUtYdAzOThRGRLoBkLc" 

# --- 2. قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('tickets.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tickets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, issue_type TEXT, location TEXT, phone TEXT, description TEXT, status TEXT DEFAULT 'جديد', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()
init_db()

# --- 3. البوت (Telegram) ---
TYPE, LOCATION, PHONE, DESCRIPTION = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🖥️ حاسبة", callback_data='Hardware'), InlineKeyboardButton("🌐 شبكة", callback_data='Network')],
                [InlineKeyboardButton("🖨️ طابعة", callback_data='Printer'), InlineKeyboardButton("💾 برمجيات", callback_data='Software')]]
    await update.message.reply_text("👋 أهلاً بك! اختر نوع المشكلة:", reply_markup=InlineKeyboardMarkup(keyboard))
    return TYPE

async def get_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['type'] = query.data
    await query.edit_message_text(f"تم اختيار: {query.data}\n📍 أين مكان المشكلة؟")
    return LOCATION

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['location'] = update.message.text
    await update.message.reply_text("📞 رقم الهاتف:")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("📝 وصف المشكلة:")
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
        tid = c.lastrowid
        conn.close()
        await update.message.reply_text(f"✅ تم فتح التذكرة #{tid}")
    except: await update.message.reply_text("خطأ في النظام!")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم الإلغاء.")
    return ConversationHandler.END

# --- تشغيل البوت (تم إزالة التخزين المؤقت لإصلاح المشكلة) ---
def run_bot_core():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(entry_points=[CommandHandler('start', start)],
        states={TYPE: [CallbackQueryHandler(get_type)], LOCATION: [MessageHandler(filters.TEXT, get_location)],
                PHONE: [MessageHandler(filters.TEXT, get_phone)], DESCRIPTION: [MessageHandler(filters.TEXT, get_description)]},
        fallbacks=[CommandHandler('cancel', cancel)])
    app.add_handler(conv)
    app.run_polling(drop_pending_updates=True) # حذف الرسائل القديمة لمنع التعليق

def start_bot_monitor():
    # فحص هل البوت يعمل؟
    is_running = any(t.name == "BotThread" for t in threading.enumerate())
    if not is_running:
        t = threading.Thread(target=run_bot_core, name="BotThread", daemon=True)
        t.start()
        return False # كان متوقفاً وتم تشغيله
    return True # يعمل حالياً

# تشغيل المراقب في كل تحديث للصفحة
bot_status = start_bot_monitor()

# --- 4. الواجهة (Dashboard) ---
# CSS
st.markdown("""<style>@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap'); * { font-family: 'Tajawal', sans-serif; } .block-container { direction: rtl; }</style>""", unsafe_allow_html=True)

# القائمة
selected = option_menu(None, ["الرئيسية", "التذاكر", "الأرشيف"], icons=["house", "list", "archive"], orientation="horizontal", default_index=1)

# --- مؤشر حالة البوت (للتشخيص) ---
st.markdown("---")
if bot_status:
    st.success("🟢 نظام البوت: **متصل ويعمل** (Thread Active)")
else:
    st.warning("🟠 نظام البوت: **جاري التشغيل...** (انتظر قليلاً)")

def get_data():
    conn = sqlite3.connect('tickets.db', check_same_thread=False)
    df = pd.read_sql_query("SELECT * FROM tickets ORDER BY id DESC", conn)
    conn.close()
    return df

# الصفحات
if selected == "الرئيسية":
    st.title("لوحة المعلومات")
    df = get_data()
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("الكل", len(df))
        c2.metric("جديد", len(df[df['status']=='جديد']))
        c3.metric("مغلق", len(df[df['status']=='مغلق']))
    else: st.info("لا توجد بيانات")

elif selected == "التذاكر":
    st.title("التذاكر النشطة")
    if st.button("تحديث"): st.rerun()
    df = get_data()
    active = df[df['status'] != 'مغلق']
    if active.empty: st.success("لا توجد مشاكل!")
    else:
        for i, row in active.iterrows():
            with st.expander(f"#{row['id']} {row['issue_type']} - {row['username']}"):
                st.write(row['description'])
                if st.button("إغلاق التذكرة", key=f"c{row['id']}"):
                    conn = sqlite3.connect('tickets.db')
                    conn.execute("UPDATE tickets SET status='مغلق' WHERE id=?", (row['id'],))
                    conn.commit()
                    conn.close()
                    st.rerun()

elif selected == "الأرشيف":
    df = get_data()
    st.dataframe(df[df['status']=='مغلق'])
