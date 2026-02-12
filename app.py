import streamlit as st
import pandas as pd
import sqlite3
import requests
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
import threading

# --- إعدادات الصفحة ---
st.set_page_config(page_title="نظام تذاكر IT", page_icon="🌐", layout="wide")

# 🔴 ضع التوكين هنا 🔴
TOKEN = "8560214645:AAFxskBVliT-KF5RJcNwCA2GNAv3Pqsgizw" 

# --- تجهيز قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('tickets.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tickets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER, username TEXT, issue_type TEXT, location TEXT, phone TEXT, description TEXT, status TEXT DEFAULT 'جديد', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- دوال البوت (Telegram Logic) ---
TYPE, LOCATION, PHONE, DESCRIPTION = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🖥️ حاسبة", callback_data='Hardware'), InlineKeyboardButton("🌐 شبكة", callback_data='Network')],
                [InlineKeyboardButton("🖨️ طابعة", callback_data='Printer'), InlineKeyboardButton("💾 برمجيات", callback_data='Software')]]
    await update.message.reply_text("مرحباً بك في دعم IT. اختر نوع المشكلة:", reply_markup=InlineKeyboardMarkup(keyboard))
    return TYPE

async def get_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['type'] = query.data
    await query.edit_message_text(f"تم اختيار: {query.data}\nالرجاء كتابة المكان (القسم/الغرفة):")
    return LOCATION

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['location'] = update.message.text
    await update.message.reply_text("رقم الهاتف الأرضي (أو اكتب 'لا يوجد'):")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("صف المشكلة باختصار:")
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    data = context.user_data
    conn = sqlite3.connect('tickets.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO tickets (user_id, username, issue_type, location, phone, description) VALUES (?, ?, ?, ?, ?, ?)",
              (user.id, user.first_name, data['type'], data['location'], data['phone'], update.message.text))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ تم فتح التذكرة! سيتم التواصل معك.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم الإلغاء.")
    return ConversationHandler.END

# --- تشغيل البوت في الخلفية ---
def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = Application.builder().token(TOKEN).build()
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
    app.add_handler(conv_handler)
    app.run_polling()

# هذه الدالة تضمن تشغيل البوت مرة واحدة فقط عند فتح الموقع
if 'bot_started' not in st.session_state:
    st.session_state['bot_started'] = True
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()

# --- واجهة الموقع (Dashboard) ---
def get_data():
    conn = sqlite3.connect('tickets.db', check_same_thread=False)
    df = pd.read_sql_query("SELECT * FROM tickets ORDER BY id DESC", conn)
    conn.close()
    return df

st.title("🌐 نظام إدارة الـ IT (Online)")
st.caption("يعمل 24/7 ومتاح من أي مكان")

if st.button('🔄 تحديث'):
    st.rerun()

df = get_data()
if not df.empty:
    for index, row in df.iterrows():
        with st.expander(f"تذكرة #{row['id']} | {row['issue_type']} | {row['username']}"):
            st.write(f"**المشكلة:** {row['description']}")
            st.write(f"**الموقع:** {row['location']}")
            # زر الرد البسيط (بدون انتظار النتيجة لتجنب التعليق)
            reply = st.text_input("الرد:", key=str(row['id']))
            if st.button("إرسال", key=f"btn_{row['id']}"):
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": row['user_id'], "text": reply})
                st.success("تم الإرسال!")
else:
    st.info("لا توجد تذاكر حالياً")