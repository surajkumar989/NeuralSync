import sqlite3
import hashlib
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory, session, make_response
import json
import os
from dotenv import load_dotenv
import logging
from functools import wraps
import time
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'neuralsync-secret-key-2024')
app.config['DATABASE'] = 'database.db'

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Hugging Face Config
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"

logger.info(f"HF API Loaded: {bool(HUGGINGFACE_API_KEY)}")

# ---------------- DATABASE ---------------- #

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_message TEXT,
            bot_response TEXT,
            timestamp TEXT,
            message_hash TEXT,
            response_time_ms INTEGER,
            tokens_used INTEGER
        )
    ''')

    conn.commit()
    conn.close()

# ---------------- SECURITY ---------------- #

def generate_hash(user_message, bot_response, timestamp):
    combined = f"{user_message}{bot_response}{timestamp}"
    return hashlib.sha256(combined.encode()).hexdigest()

# ---------------- SAVE CHAT ---------------- #

def save_chat(session_id, user_message, bot_response, response_time_ms=0, tokens_used=0):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    message_hash = generate_hash(user_message, bot_response, timestamp)

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO chat_history (session_id, user_message, bot_response, timestamp, message_hash, response_time_ms, tokens_used)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (session_id, user_message, bot_response, timestamp, message_hash, response_time_ms, tokens_used))

    conn.commit()
    conn.close()

    return {
        "timestamp": timestamp,
        "hash": message_hash
    }

# ---------------- RATE LIMIT ---------------- #

def rate_limit(max_requests=20, window=60):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if 'rate_limit' not in session:
                session['rate_limit'] = {'count': 0, 'window_start': time.time()}

            rate_data = session['rate_limit']

            if time.time() - rate_data['window_start'] > window:
                rate_data['count'] = 0
                rate_data['window_start'] = time.time()

            if rate_data['count'] >= max_requests:
                return jsonify({'error': 'Rate limit exceeded'}), 429

            rate_data['count'] += 1
            session.modified = True
            return f(*args, **kwargs)
        return wrapped
    return decorator

# ---------------- HUGGING FACE API ---------------- #

def get_huggingface_response(user_message):
    if not HUGGINGFACE_API_KEY:
        raise Exception("HF API key not found")

    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": user_message,
        "parameters": {
            "max_new_tokens": 300,
            "temperature": 0.7,
            "return_full_text": False
        }
    }

    start_time = time.time()

    response = requests.post(
        f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}",
        headers=headers,
        json=payload,
        timeout=60
    )

    response_time_ms = int((time.time() - start_time) * 1000)

    if response.status_code != 200:
        raise Exception(response.text)

    data = response.json()

    bot_text = data[0]["generated_text"]

    tokens_used = len(bot_text.split())

    return {
        "text": bot_text.strip(),
        "response_time_ms": response_time_ms,
        "tokens_used": tokens_used,
        "model": HF_MODEL
    }


# ---------------- FALLBACK ---------------- #

def get_local_response(user_message):
    text = f"I received: {user_message}. This message is secured using SHA-256 hashing."
    return {
        "text": text,
        "response_time_ms": 50,
        "tokens_used": len(text.split()),
        "model": "local-fallback"
    }

# ---------------- MAIN BOT ---------------- #

def get_bot_response(user_message):
    user_message = user_message.strip()
    if not user_message:
        return get_local_response("empty")

    try:
        if HUGGINGFACE_API_KEY:
            return get_huggingface_response(user_message)
        else:
            return get_local_response(user_message)
    except Exception as e:
        logger.warning(f"HF failed: {e}")
        return get_local_response(user_message)

# ---------------- SESSION ---------------- #

@app.before_request
def manage_session():
    if 'user_id' not in session:
        session['user_id'] = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]

# ---------------- ROUTES ---------------- #

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
@rate_limit(max_requests=20, window=60)
def api_chat():
    data = request.get_json()
    user_message = data.get('message', '').strip()
    session_id = session.get('user_id')

    if not user_message:
        return jsonify({'error': 'Empty message'}), 400

    bot_data = get_bot_response(user_message)

    chat_info = save_chat(
        session_id,
        user_message,
        bot_data['text'],
        bot_data['response_time_ms'],
        bot_data['tokens_used']
    )

    return jsonify({
        "success": True,
        "user_message": user_message,
        "bot_response": bot_data['text'],
        "timestamp": chat_info['timestamp'],
        "hash": chat_info['hash'],
        "short_hash": chat_info['hash'][:16] + "...",
        "model_used": bot_data['model'],
        "tokens_used": bot_data['tokens_used']
    })

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/history')
def history():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT user_message, bot_response, timestamp, message_hash FROM chat_history ORDER BY id DESC LIMIT 20")
    chats = cursor.fetchall()
    conn.close()

    return render_template('history.html', chats=chats)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/contact')
def contact():
    return render_template('privacy.html')

@app.route('/api/health')
def health():
    return jsonify({
        "status": "ok",
        "hf_api": bool(HUGGINGFACE_API_KEY),
        "time": datetime.now().isoformat()
    })

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

# ---------------- RUN ---------------- #

if __name__ == "__main__":
    init_db()
    logger.info("Starting NeuralSync server...")
    app.run(debug=True)
