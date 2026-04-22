from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from supabase import create_client
from groq import Groq
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import os
import json

load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app)

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

scheduler = BackgroundScheduler()
scheduler.start()

IST = timezone(timedelta(hours=5, minutes=30))


def get_ist_time():
    return datetime.now(IST).strftime("%I:%M %p IST, %d %B %Y")


def extract_reminder_intent(message):
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": """You are a time extraction assistant.
If the user's message contains a request to be reminded about something after a certain time, extract it.
Respond ONLY in this exact JSON format with no extra text:
{"is_reminder": true, "delay_seconds": 60, "about": "what to remind about"}
If there is no reminder request respond ONLY with:
{"is_reminder": false}"""
                },
                {"role": "user", "content": message}
            ]
        )
        result = json.loads(response.choices[0].message.content.strip())
        return result
    except Exception as e:
        print(f"REMINDER EXTRACT ERROR: {e}")
        return {"is_reminder": False}


def get_time_context(user_id):
    result = supabase.table("conversations").select("*").eq("user_id", user_id).order("timestamp", desc=True).limit(10).execute()
    messages = result.data
    time_context = ""

    if messages:
        last_msg_time = datetime.fromisoformat(messages[0]["timestamp"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - last_msg_time
        total_seconds = diff.total_seconds()

        if total_seconds < 120:
            time_context = ""
        elif total_seconds < 3600:
            mins = int(total_seconds // 60)
            time_context = f"The user was away for {mins} minutes."
        elif total_seconds < 86400:
            hours = int(total_seconds // 3600)
            time_context = f"The user was away for {hours} hour(s)."
        else:
            days = diff.days
            time_context = f"The user was away for {days} day(s). Give them a warm welcome back."
    else:
        time_context = "This is the first time the user is talking to Loki."

    return messages, time_context


def generate_loki_response(user_id, user_message, system_prompt):
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        reply = response.choices[0].message.content

        supabase.table("conversations").insert({
            "user_id": user_id,
            "message": reply,
            "role": "assistant",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }).execute()

        return reply
    except Exception as e:
        print(f"GROQ ERROR: {e}")
        return None


def send_scheduled_reminder(user_id, reminder_message):
    system_prompt = f"""You are Loki, a time-aware personal AI assistant. You are witty, warm, and slightly mischievous.
You are proactively reaching out to remind the user about something they asked you to remind them about.
Be natural, friendly and brief. Do not be robotic.
If the user asks for a reminder but doesn't specify what to remind them about, ask them what the reminder is for BEFORE confirming it. Do not assume or invent a topic.
Current time: {get_ist_time()}
"""
    generate_loki_response(user_id, f"[REMINDER] {reminder_message}", system_prompt)
    print(f"REMINDER SENT for {user_id}: {reminder_message}")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_id = data.get("user_id", "default_user")
    user_message = data.get("message", "")

    supabase.table("conversations").insert({
        "user_id": user_id,
        "message": user_message,
        "role": "user",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }).execute()

    reminder_intent = extract_reminder_intent(user_message)
    if reminder_intent.get("is_reminder"):
        delay_seconds = reminder_intent.get("delay_seconds", 60)
        about = reminder_intent.get("about", user_message)
        run_time = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        scheduler.add_job(
            send_scheduled_reminder,
            'date',
            run_date=run_time,
            args=[user_id, about],
            id=f"reminder_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
            replace_existing=False
        )

    messages, time_context = get_time_context(user_id)

    history = ""
    for msg in reversed(messages[1:6]):
        history += f"{msg['role'].capitalize()}: {msg['message']}\n"

    system_prompt = system_prompt = f"""You are Loki, a time-aware personal AI assistant. You are witty, warm, and slightly mischievous.

{("Note (internal only, do not mention unless user asks): " + time_context) if time_context else ""}

Do NOT mention the current time or date unless the user explicitly asks for it.
If the user asks for a reminder but doesn't specify what to remind them about, ask them first.
If the user asks to remind them about something after a certain time, confirm it naturally.

Recent conversation history:
{history}

Current time: {get_ist_time()}
"""

    reply = generate_loki_response(user_id, user_message, system_prompt)

    if not reply:
        return jsonify({"reply": "The Bifrost is down. Try again.", "time_context": time_context})

    return jsonify({"reply": reply, "time_context": time_context})


@app.route("/reminder", methods=["POST"])
def set_reminder():
    data = request.json
    message = data.get("message", "")
    delay_seconds = data.get("delay_seconds", 60)
    user_id = data.get("user_id", "default_user")

    run_time = datetime.datetime.now(timezone.utc)() + timedelta(seconds=delay_seconds)

    scheduler.add_job(
        send_scheduled_reminder,
        'date',
        run_date=run_time,
        args=[user_id, message],
        id=f"reminder_{user_id}_{int(datetime.utcnow().timestamp())}",
        replace_existing=False
    )

    return jsonify({"status": "Reminder set!", "delay_seconds": delay_seconds})


@app.route("/poll", methods=["GET"])
def poll():
    user_id = request.args.get("user_id", "default_user")
    after = request.args.get("after", "")

    query = supabase.table("conversations").select("*").eq("user_id", user_id).eq("role", "assistant").order("timestamp", desc=False)

    if after:
        after = after.replace(" ", "T")
        query = query.gt("timestamp", after)

    result = query.execute()
    return jsonify({"messages": result.data})


if __name__ == "__main__":
    app.run(debug=True)