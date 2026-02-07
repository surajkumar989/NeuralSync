import sqlite3
import hashlib
from datetime import datetime
from flask import Flask, render_template, request

app = Flask(__name__)

# Database initialization
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_message TEXT NOT NULL,
            bot_response TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            message_hash TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

# Helper function to generate SHA-256 hash
def generate_hash(user_message, bot_response, timestamp):
    """Generate SHA-256 hash for message security"""
    combined = f"{user_message}{bot_response}{timestamp}"
    return hashlib.sha256(combined.encode()).hexdigest()

# Helper function to save chat
def save_chat(user_message, bot_response):
    """Save chat to database with hash"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    message_hash = generate_hash(user_message, bot_response, timestamp)
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO chat_history (user_message, bot_response, timestamp, message_hash)
        VALUES (?, ?, ?, ?)
    ''', (user_message, bot_response, timestamp, message_hash))
    
    conn.commit()
    conn.close()
    
    return message_hash

@app.route('/', methods=['GET', 'POST'])
def home():
    response = None
    
    if request.method == 'POST':
        user_message = request.form.get('message', '')
        
        # Demo bot response (later replace with AI API)
        bot_response = f"You said: {user_message}"
        
        # Save to database and get hash
        message_hash = save_chat(user_message, bot_response)
        
        response = {
            'message': bot_response,
            'hash': message_hash[:16] + '...'  # Show shortened hash
        }
    
    return render_template('home.html', response=response)

@app.route('/history')
def history():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, user_message, bot_response, timestamp, message_hash
        FROM chat_history
        ORDER BY id DESC
    ''')
    
    chats = cursor.fetchall()
    conn.close()
    
    return render_template('history.html', chats=chats)

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Total messages count
    cursor.execute('SELECT COUNT(*) FROM chat_history')
    total_messages = cursor.fetchone()[0]
    
    # Total conversations (unique chats)
    total_conversations = total_messages  # For demo, each message = 1 conversation
    
    # Recent activity (last 5 chats)
    cursor.execute('''
        SELECT user_message, bot_response, timestamp
        FROM chat_history
        ORDER BY id DESC
        LIMIT 5
    ''')
    recent_activity = cursor.fetchall()
    
    # Messages per day (for chart data)
    cursor.execute('''
        SELECT DATE(timestamp) as date, COUNT(*) as count
        FROM chat_history
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
        LIMIT 7
    ''')
    daily_stats = cursor.fetchall()
    
    conn.close()
    
    stats = {
        'total_messages': total_messages,
        'total_conversations': total_conversations,
        'recent_activity': recent_activity,
        'daily_stats': daily_stats
    }
    
    return render_template('dashboard.html', stats=stats)

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    init_db()  # Initialize database on startup
    app.run(debug=True)