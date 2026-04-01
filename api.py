import json
import time
import threading
import requests
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================== CONFIG ==================
TOKEN = "8542782643:AAFEZ_tKUB7WfV2TPzwyX2-YmnoJQLcrNS4"
OWNER_ID = 6004016819
API_FILE = "apis9.json"
KEY_FILE = "keys.json"
PORT = 8888

app = Flask(__name__)

# ================== FILE SYSTEM ==================
def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def load_apis():
    return load_json(API_FILE, {"apis": []})["apis"]

def save_apis(apis):
    save_json(API_FILE, {"apis": apis})

def load_keys():
    return load_json(KEY_FILE, {"keys": {}})["keys"]

def save_keys(keys):
    save_json(KEY_FILE, {"keys": keys})

# ================== OWNER CHECK ==================
def is_owner(update):
    return update.effective_user.id == OWNER_ID

# ================== KEY SYSTEM ==================
def check_key(key):
    keys = load_keys()

    if key not in keys:
        return False, "Invalid Key"

    k = keys[key]
    now = time.time()

    if k["expiry"] and now > k["expiry"]:
        return False, "Key Expired"

    if now > k["reset_time"]:
        k["used"] = 0
        k["reset_time"] = now + 3600

    if k["limit_per_hour"] is not None:
        if k["used"] >= k["limit_per_hour"]:
            return False, "Rate Limit Exceeded"

    k["used"] += 1
    keys[key] = k
    save_keys(keys)

    return True, "OK"

# ================== PARSER ==================
def extract_data(res):
    try:
        if "result" in res:
            r = res["result"]
            return r.get("number"), r.get("country"), r.get("country_code")

        return (
            res.get("number") or res.get("phone"),
            res.get("country"),
            res.get("country_code") or res.get("cc"),
        )
    except:
        return None, None, None

# ================== SEARCH ==================
def search(query):
    print("🔍 Searching:", query)

    apis = load_apis()

    for api in apis:
        try:
            url = api.replace("{query}", query)
            print("🌐 Calling:", url)

            res = requests.get(url, timeout=5)

            try:
                r = res.json()
            except:
                print("❌ Invalid JSON:", res.text)
                continue

            num, country, cc = extract_data(r)

            if num and country and cc:
                return {
                    "success": True,
                    "owner": "https://HEARTLESSSUKUNA\nDM FOR BUY API @HeartLessSukuna",
                    "result": {
                        "success": True,
                        "spell": query,
                        "country": country,
                        "country_code": cc,
                        "number": num
                    }
                }

        except Exception as e:
            print("❌ API Error:", e)
            continue

    return {
        "success": True,
        "owner": "https://HEARTLESSSUKUNA\nDM FOR BUY API @HeartLessSukuna",
        "result": {
            "success": False,
            "spell": query,
            "number": "Not Found"
        }
    }

# ================== API ==================
@app.route("/api")
def api():
    try:
        key = request.args.get("key")
        spell = request.args.get("spell")

        if not key or not spell:
            return jsonify({"error": "Missing key or spell"})

        ok, msg = check_key(key)
        if not ok:
            return jsonify({"error": msg})

        return jsonify(search(spell))

    except Exception as e:
        print("🔥 SERVER ERROR:", e)
        return jsonify({"error": "Server Error"})

# ================== TELEGRAM ==================

# 🔥 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return await update.message.reply_text("❌ Not Authorized")

    await update.message.reply_text(
        "🔥 API Control Panel Active\n\n"
        "/addapi <url>\n"
        "/listapi\n"
        "/addkey <key> [limit] [hours]\n"
        "/listkey\n"
        "/removekey <key>"
    )

# ➕ ADD API
async def addapi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return await update.message.reply_text("❌ Not Authorized")

    try:
        url = context.args[0]
        apis = load_apis()
        apis.insert(0, url)
        save_apis(apis)
        await update.message.reply_text("✅ API Added")
    except:
        await update.message.reply_text("Usage: /addapi <url>")

# 📄 LIST API
async def listapi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return await update.message.reply_text("❌ Not Authorized")

    apis = load_apis()
    await update.message.reply_text("\n".join(apis) or "No APIs")

# 🔐 ADD KEY
async def addkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return await update.message.reply_text("❌ Not Authorized")

    try:
        key = context.args[0]
        limit = None
        expiry = None

        if len(context.args) >= 2:
            limit = int(context.args[1])

        if len(context.args) == 3:
            expiry = time.time() + int(context.args[2]) * 3600

        keys = load_keys()

        keys[key] = {
            "limit_per_hour": limit,
            "used": 0,
            "reset_time": time.time() + 3600,
            "expiry": expiry
        }

        save_keys(keys)

        await update.message.reply_text("✅ Key Added")

    except:
        await update.message.reply_text("Usage: /addkey <key> [limit] [hours]")

# 📄 LIST KEYS
async def listkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return await update.message.reply_text("❌ Not Authorized")

    keys = load_keys()
    msg = ""

    for k, v in keys.items():
        msg += f"{k} | limit={v['limit_per_hour']} | expiry={v['expiry']}\n"

    await update.message.reply_text(msg or "No Keys")

# ❌ REMOVE KEY
async def removekey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return await update.message.reply_text("❌ Not Authorized")

    try:
        key = context.args[0]
        keys = load_keys()
        keys.pop(key, None)
        save_keys(keys)
        await update.message.reply_text("❌ Key Removed")
    except:
        await update.message.reply_text("Usage: /removekey <key>")

# ================== BOT ==================
def run_bot():
    bot = ApplicationBuilder().token(TOKEN).build()

    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("addapi", addapi))
    bot.add_handler(CommandHandler("listapi", listapi))
    bot.add_handler(CommandHandler("addkey", addkey))
    bot.add_handler(CommandHandler("listkey", listkey))
    bot.add_handler(CommandHandler("removekey", removekey))

    print("🤖 BOT STARTED")
    bot.run_polling(close_loop=False)

# ================== MAIN ==================
if __name__ == "__main__":
    try:
        print("🚀 SERVER STARTED")

        app.run(
            host="0.0.0.0",
            port=PORT,
            debug=False
        )

    except Exception as e:
        print("🔥 SERVER CRASH:", e)

