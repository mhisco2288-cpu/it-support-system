import streamlit as st
import pandas as pd
import sqlite3
import requests
import time
import asyncio
import threading
import nest_asyncio
import plotly.express as px
import io
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
from streamlit_option_menu import option_menu

# --- 0. تهيئة النظام ---
nest_asyncio.apply()
st.set_page_config(page_title="IT Nexus Pro", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# 🎨 تصميم الواجهة الاحترافي (Cyberpunk Glassmorphism)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;700;900&display=swap');
    * { font-family: 'Cairo', sans-serif !important; }
    
    /* الخلفية المتدرجة */
    .stApp { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: white; }
    
    /* البطاقات الزجاجية */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        transition: transform 0.3s ease;
    }
    div[data-testid="metric-container"]:hover { transform: translateY(-5px); border-color: #00d2ff; }
    div[data-testid="stMetricValue"] { color: #00d2ff !important; text-shadow: 0 0 10px rgba(0, 210, 255, 0.6); }
    
    /* الأزرار والحقول */
    .stButton>button { background: linear-gradient(90deg, #00d2ff, #3a7bd5); border: none; color: white; border-radius: 8px; font-weight: bold; }
    .stTextInput>div>div>input { background-color: rgba(255,255,255,0.1); color: white; border-radius: 8px; border: 1px solid #444; }
    
    /* الجداول */
    div[data-testid="stDataFrame"] { background: rgba(0, 0, 0, 0.3); border-radius: 15px; padding: 15px; border: 1px solid rgba(255,255,255,0.1); }
    
    /* القوائم */
    .css-1v0mbdj { direction: rtl; }
    .block-container { direction: rtl; }
</style>
""", unsafe_allow_html=True)

# 🔴🔴🔴 إعدادات الاتصال 🔴🔴🔴
TOKEN = "7690158561:AAH9kiOjUNZIErzlWUtYdAzOThRGRLoBkLc" 

# --- 1. إدارة قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('nexus_pro.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tickets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ticket_code TEXT,
                  user_id INTEGER,
                  username TEXT,
                  category TEXT,
                  priority TEXT,
                  location TEXT,
                  phone TEXT,
                  description TEXT,
                  status TEXT DEFAULT 'جديد',
                  admin_reply TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- 2. محرك البوت (Telegram Engine) ---
CAT, PRIO, LOC, PHONE, DESC = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    await update.message.reply_text(f"🚀 أهلاً بك {user} في نظام الدعم الفني الذكي.\nلتقديم طلب صيانة، اضغط الزر أدناه:", 
                                   reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📝 فتح تذكرة جديدة", callback_data='NEW')]]))
    return CAT

async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🖥️ أجهزة / Hardware", callback_data='Hardware'), InlineKeyboardButton("🌐 شبكة / Network", callback_data='Network')],
        [InlineKeyboardButton("🖨️ طابعات / Printers", callback_data='Printers'), InlineKeyboardButton("💾 أنظمة / Software", callback_data='Software')]
    ]
    await query.edit_message_text("📌 حدد نوع المشكلة:", reply_markup=InlineKeyboardMarkup(keyboard))
    return PRIO

async def select_priority(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['cat'] = query.data
    keyboard = [[InlineKeyboardButton("🔥 عاجل جداً (توقف عمل)", callback_data='Urgent')],
                [InlineKeyboardButton("⚡ متوسطة", callback_data='Normal'), InlineKeyboardButton("🐢 منخفضة", callback_data='Low')]]
    await query.edit_message_text(f"القسم: {query.data}\n🚦 ما مدى استعجال الحالة؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return LOC

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['prio'] = query.data
    await query.edit_message_text(f"الأولوية: {query.data}\n\n📍 اكتب مكانك (القسم / الغرفة):")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['loc'] = update.message.text
    await update.message.reply_text("📞 رقم للتواصل (أرضي أو موبايل):")
    return DESC

async def get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("📝 صف المشكلة بالتفصيل:")
    return DESC + 1

async def save_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    data = context.user_data
    desc = update.message.text
    ticket_code = f"TK-{int(time.time())%10000}"
    
    try:
        conn = sqlite3.connect('nexus_pro.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT INTO tickets (ticket_code, user_id, username, category, priority, location, phone, description) VALUES (?,?,?,?,?,?,?,?)",
                  (ticket_code, user.id, user.first_name, data['cat'], data['prio'], data['loc'], data['phone'], desc))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ **تم تسجيل الطلب!**\n🎫 رقم التذكرة: `{ticket_code}`\nسيتم إشعارك عند الرد.", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text("⚠️ خطأ في النظام.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم الإلغاء.")
    return ConversationHandler.END

# تشغيل البوت
def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(select_category, pattern='NEW'), CommandHandler('start', start)],
        states={
            CAT: [CallbackQueryHandler(select_category)],
            PRIO: [CallbackQueryHandler(select_priority)],
            LOC: [MessageHandler(filters.TEXT, get_location)],
            PHONE: [MessageHandler(filters.TEXT, get_phone)],
            DESC: [MessageHandler(filters.TEXT, get_desc)],
            DESC+1: [MessageHandler(filters.TEXT, save_ticket)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    app.add_handler(conv)
    loop.run_until_complete(app.bot.delete_webhook(drop_pending_updates=True))
    app.run_polling(drop_pending_updates=True)

if not any(t.name == "BotThread" for t in threading.enumerate()):
    t = threading.Thread(target=run_bot, name="BotThread", daemon=True)
    t.start()

# --- 3. واجهة النظام (Dashboard) ---
def get_data():
    conn = sqlite3.connect('nexus_pro.db')
    df = pd.read_sql_query("SELECT * FROM tickets ORDER BY created_at DESC", conn)
    conn.close()
    return df

# القائمة الرئيسية
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/906/906343.png", width=80)
    st.title("IT Nexus Pro")
    selected = option_menu("القائمة", ["لوحة القيادة", "التذاكر والردود", "إضافة يدوية", "تصدير إكسل"], 
                          icons=['speedometer2', 'chat-dots', 'plus-circle', 'file-earmark-excel'], default_index=0)

# === الصفحة 1: لوحة القيادة ===
if selected == "لوحة القيادة":
    st.markdown("## 📊 مؤشرات الأداء الحيوية")
    df = get_data()
    
    if not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 الكل", len(df))
        c2.metric("🔴 جديد", len(df[df['status']=='جديد']), delta_color="inverse")
        c3.metric("🟡 قيد العمل", len(df[df['status']=='قيد العمل']))
        c4.metric("✅ منجز", len(df[df['status']=='مكتمل']))
        
        st.markdown("---")
        
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("توزيع المشاكل")
            fig1 = px.pie(df, names='category', hole=0.5, color_discrete_sequence=px.colors.qualitative.Cyan)
            st.plotly_chart(fig1, use_container_width=True)
        with g2:
            st.subheader("الأولوية والحالة")
            fig2 = px.bar(df, x='status', color='priority', barmode='group')
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("النظام جاهز لاستقبال البيانات...")

# === الصفحة 2: التذاكر والردود الذكية ===
elif selected == "التذاكر والردود":
    st.markdown("## 🎫 إدارة التذاكر")
    if st.button("🔄 تحديث القائمة"): st.rerun()
    
    df = get_data()
    active_tickets = df[df['status'] != 'مكتمل']
    
    if active_tickets.empty:
        st.success("🎉 لا توجد تذاكر نشطة حالياً!")
    else:
        for i, row in active_tickets.iterrows():
            border = "red" if row['priority'] == 'Urgent' else "cyan"
            with st.expander(f"📌 {row['ticket_code']} | {row['category']} | {row['username']}"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown(f"**الوصف:** {row['description']}")
                    st.markdown(f"📍 `{row['location']}` | 📞 `{row['phone']}`")
                    st.caption(f"تاريخ: {row['created_at']}")
                
                with c2:
                    st.markdown("##### ⚙️ الإجراءات")
                    new_st = st.selectbox("الحالة", ["جديد", "قيد العمل", "مكتمل"], key=f"s_{row['id']}", index=["جديد", "قيد العمل", "مكتمل"].index(row['status']))
                    
                    reply_msg = st.text_area("الرد على الموظف:", key=f"r_{row['id']}")
                    
                    if st.button("حفظ وإرسال 🚀", key=f"btn_{row['id']}"):
                        # تحديث القاعدة
                        conn = sqlite3.connect('nexus_pro.db')
                        conn.execute("UPDATE tickets SET status=?, admin_reply=? WHERE id=?", (new_st, reply_msg, row['id']))
                        conn.commit()
                        conn.close()
                        
                        # إرسال للتليجرام
                        if reply_msg:
                            try:
                                msg_text = f"🔔 **تحديث على التذكرة {row['ticket_code']}**\n\nالحالة: {new_st}\n💬 رد الدعم: {reply_msg}"
                                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": row['user_id'], "text": msg_text, "parse_mode": "Markdown"})
                                st.toast("تم الإرسال للموظف بنجاح!", icon="✅")
                            except: st.error("فشل الإرسال للتليجرام")
                        
                        time.sleep(1)
                        st.rerun()

# === الصفحة 3: إضافة يدوية ===
elif selected == "إضافة يدوية":
    st.markdown("## ➕ تسجيل تذكرة (هاتف/شفهي)")
    with st.form("manual_add"):
        c1, c2 = st.columns(2)
        username = c1.text_input("اسم الموظف")
        phone = c2.text_input("رقم الهاتف")
        cat = c1.selectbox("القسم", ["Hardware", "Network", "Software", "Printers"])
        prio = c2.selectbox("الأولوية", ["Urgent", "Normal", "Low"])
        loc = st.text_input("الموقع")
        desc = st.text_area("وصف المشكلة")
        
        if st.form_submit_button("تسجيل التذكرة"):
            conn = sqlite3.connect('nexus_pro.db')
            code = f"MAN-{int(time.time())%10000}"
            conn.execute("INSERT INTO tickets (ticket_code, user_id, username, category, priority, location, phone, description) VALUES (?,0,?,?,?,?,?,?)",
                        (code, username, cat, prio, loc, phone, desc))
            conn.commit()
            conn.close()
            st.success(f"تم التسجيل برقم {code}")

# === الصفحة 4: تصدير إكسل ===
elif selected == "تصدير إكسل":
    st.markdown("## 📥 أرشفة البيانات")
    df = get_data()
    st.dataframe(df)
    
    # تحويل لملف اكسل
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Tickets')
        
    st.download_button(
        label="📥 تحميل التقرير (Excel)",
        data=buffer.getvalue(),
        file_name=f"IT_Report_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.ms-excel"
    )
