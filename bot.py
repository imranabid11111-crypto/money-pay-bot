import os, threading, logging
from flask import Flask, request, jsonify, render_template
import telebot
from telebot import types
from dotenv import load_dotenv
from database import init_db, get_user, save_pending_ref, complete_referral, create_withdrawal, list_withdrawals, update_withdrawal, get_stats
from security import validate_init_data

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip()
CHANNEL_IDS = [x.strip() for x in os.getenv("CHANNEL_IDS", "").split(",") if x.strip()]
CHANNEL_LINKS = [x.strip() for x in os.getenv("CHANNEL_LINKS", "").split(",") if x.strip()]
REWARD = 5
MIN_WITHDRAW = 50

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Copy .env.example to .env and set your token.")
if len(CHANNEL_IDS) != 4 or len(CHANNEL_LINKS) != 4:
    raise RuntimeError("Set exactly four CHANNEL_IDS and four CHANNEL_LINKS in .env")

logging.basicConfig(level=logging.INFO)
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

def membership_keyboard():
    kb = types.InlineKeyboardMarkup()
    for i, link in enumerate(CHANNEL_LINKS, 1):
        kb.add(types.InlineKeyboardButton(f"📢 Join Channel {i}", url=link))
    kb.add(types.InlineKeyboardButton("✅ Verify Membership", callback_data="verify"))
    return kb

def check_memberships(user_id):
    missing = []
    for channel in CHANNEL_IDS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ("creator", "administrator", "member"):
                missing.append(channel)
        except Exception:
            logging.exception("Membership check failed for %s", channel)
            missing.append(channel)
    return missing

def open_app_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if WEBAPP_URL:
        kb.add(types.KeyboardButton("🚀 Open MONEY PAY", web_app=types.WebAppInfo(url=WEBAPP_URL)))
    return kb

@bot.message_handler(commands=["start"])
def start(message):
    uid = message.from_user.id
    parts = message.text.split(maxsplit=1)
    referrer = None
    if len(parts) > 1 and parts[1].startswith("ref_"):
        try:
            candidate = int(parts[1][4:])
            if candidate != uid:
                referrer = candidate
        except ValueError:
            pass
    save_pending_ref(uid, referrer)
    missing = check_memberships(uid)
    if missing:
        bot.send_message(
            message.chat.id,
            "স্বাগতম <b>MONEY PAY</b>!\n\nMini App ব্যবহার করতে নিচের ৫টি চ্যানেলে Join করে Verify Membership চাপুন।",
            reply_markup=membership_keyboard()
        )
    else:
        complete_referral(uid, REWARD)
        bot.send_message(message.chat.id, "✅ Membership verified. MONEY PAY ব্যবহার করতে নিচের বাটন চাপুন।",
                         reply_markup=open_app_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "verify")
def verify(call):
    uid = call.from_user.id
    missing = check_memberships(uid)
    if missing:
        bot.answer_callback_query(call.id, "সব ৫টি চ্যানেলে Join হয়নি।", show_alert=True)
        return
    complete_referral(uid, REWARD)
    bot.answer_callback_query(call.id, "Membership verified!")
    bot.send_message(call.message.chat.id, "✅ সফলভাবে Verify হয়েছে। এখন Mini App খুলুন।",
                     reply_markup=open_app_keyboard())

@bot.message_handler(commands=["admin"])
def admin(message):
    if message.from_user.id != ADMIN_ID:
        return
    stats = get_stats()
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📥 Pending withdrawals", callback_data="admin_pending"))
    bot.send_message(message.chat.id,
        f"<b>MONEY PAY Admin</b>\nUsers: {stats['users']}\nReferrals: {stats['referrals']}\nPending: {stats['pending']}",
        reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "admin_pending")
def pending(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Not allowed", show_alert=True); return
    rows = list_withdrawals("pending")
    if not rows:
        bot.send_message(call.message.chat.id, "কোনো pending withdrawal নেই।"); return
    for wid, uid, amount, method, account in rows:
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("✅ Approve", callback_data=f"wd_ok_{wid}"),
               types.InlineKeyboardButton("❌ Reject", callback_data=f"wd_no_{wid}"))
        bot.send_message(call.message.chat.id,
            f"Request #{wid}\nUser: <code>{uid}</code>\nAmount: ৳{amount}\nMethod: {method}\nAccount: <code>{account}</code>",
            reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith(("wd_ok_", "wd_no_")))
def decide_withdrawal(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Not allowed", show_alert=True); return
    approve = call.data.startswith("wd_ok_")
    wid = int(call.data.split("_")[-1])
    row = update_withdrawal(wid, "approved" if approve else "rejected")
    if not row:
        bot.answer_callback_query(call.id, "Request already handled or not found.", show_alert=True); return
    uid, amount = row
    if approve:
        bot.send_message(uid, f"✅ আপনার ৳{amount} withdrawal approve হয়েছে। Admin আপনার পেমেন্ট পাঠাবেন।")
    else:
        bot.send_message(uid, f"❌ আপনার ৳{amount} withdrawal reject হয়েছে। ব্যালেন্স ফেরত দেওয়া হয়েছে।")
    bot.answer_callback_query(call.id, "Updated")
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

@app.get("/")
def home():
    return render_template("index.html", bot_username=os.getenv("BOT_USERNAME", "").lstrip("@"))

def authorized_user():
    raw = request.headers.get("X-Telegram-Init-Data", "")
    data = validate_init_data(raw, TOKEN)
    if not data:
        return None
    try:
        import json
        user = json.loads(data["user"])
        uid = int(user["id"])
    except Exception:
        return None
    if check_memberships(uid):
        return None
    return uid

@app.get("/api/me")
def api_me():
    uid = authorized_user()
    if not uid:
        return jsonify({"error": "verification_required"}), 403
    return jsonify(get_user(uid, REWARD, MIN_WITHDRAW))

@app.post("/api/withdraw")
def api_withdraw():
    uid = authorized_user()
    if not uid:
        return jsonify({"error": "verification_required"}), 403
    body = request.get_json(silent=True) or {}
    method = str(body.get("method", ""))
    account = str(body.get("account", "")).strip()
    if method not in ("bKash", "Nagad") or not account or len(account) > 40:
        return jsonify({"error": "invalid_details"}), 400
    ok, message = create_withdrawal(uid, MIN_WITHDRAW, method, account)
    return jsonify({"ok": ok, "message": message}), (200 if ok else 400)

def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")), threaded=True)

if __name__ == "__main__":
    init_db()
    threading.Thread(target=run_flask, daemon=True).start()
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
