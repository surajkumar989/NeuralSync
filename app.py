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

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'neuralsync-secret-key-2024')
app.config['DATABASE'] = 'database.db'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Google Gemini AI
GEMINI_API_KEY = os.environ.get('GOOGLE_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Gemini API configured successfully")
else:
    logger.warning("GOOGLE_API_KEY not found in environment. Using local responses only.")

# Database initialization
def init_db():
    """Initialize the database with required tables"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Chat history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                message_hash TEXT NOT NULL,
                conversation_id INTEGER,
                response_time_ms INTEGER,
                tokens_used INTEGER
            )
        ''')
        
        # Analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        # User sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                last_activity TEXT NOT NULL,
                message_count INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0
            )
        ''')
        
        # API usage table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                model_used TEXT,
                tokens_used INTEGER,
                response_time_ms INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

# Helper function to generate SHA-256 hash
def generate_hash(user_message, bot_response, timestamp):
    """Generate SHA-256 hash for message security"""
    combined = f"{user_message}{bot_response}{timestamp}"
    return hashlib.sha256(combined.encode()).hexdigest()

# Helper function to save chat
def save_chat(session_id, user_message, bot_response, response_time_ms=0, tokens_used=0, conversation_id=None):
    """Save chat to database with hash"""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        message_hash = generate_hash(user_message, bot_response, timestamp)
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Save chat message
        cursor.execute('''
            INSERT INTO chat_history (session_id, user_message, bot_response, timestamp, message_hash, 
                                     conversation_id, response_time_ms, tokens_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, user_message, bot_response, timestamp, message_hash, conversation_id, response_time_ms, tokens_used))
        
        # Update session activity
        cursor.execute('''
            INSERT OR REPLACE INTO user_sessions (session_id, created_at, last_activity, message_count, total_tokens)
            VALUES (?, COALESCE((SELECT created_at FROM user_sessions WHERE session_id = ?), ?), ?, 
                    COALESCE((SELECT message_count FROM user_sessions WHERE session_id = ?), 0) + 1,
                    COALESCE((SELECT total_tokens FROM user_sessions WHERE session_id = ?), 0) + ?)
        ''', (session_id, session_id, timestamp, timestamp, session_id, session_id, tokens_used))
        
        # Log API usage if tokens were used
        if tokens_used > 0:
            cursor.execute('''
                INSERT INTO api_usage (session_id, timestamp, model_used, tokens_used, response_time_ms)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, timestamp, 'gemini-pro', tokens_used, response_time_ms))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Chat saved for session {session_id[:8]}, tokens: {tokens_used}")
        
        return {
            'timestamp': timestamp,
            'hash': message_hash,
            'response_time_ms': response_time_ms
        }
    except Exception as e:
        logger.error(f"Error saving chat: {e}")
        return None

# Rate limiting decorator
def rate_limit(max_requests=10, window=60):
    """Simple rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if 'rate_limit' not in session:
                session['rate_limit'] = {'count': 0, 'window_start': time.time()}
            
            rate_data = session['rate_limit']
            
            # Reset if window has passed
            if time.time() - rate_data['window_start'] > window:
                rate_data['count'] = 0
                rate_data['window_start'] = time.time()
            
            # Check rate limit
            if rate_data['count'] >= max_requests:
                return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
            
            rate_data['count'] += 1
            session.modified = True
            
            return f(*args, **kwargs)
        return wrapped
    return decorator

# AI Response Generator using Google Gemini
def get_gemini_response(user_message):
    """Generate bot response using Google Gemini API"""
    if not GEMINI_API_KEY:
        raise Exception("Gemini API key not configured")
    
    try:
        # Initialize the model
        model = genai.GenerativeModel('gemini-pro')
        
        # Prepare system prompt
        system_prompt = """You are NeuralSync, a transparent AI assistant. Every conversation is cryptographically secured with SHA-256 hashing for complete transparency.

Guidelines:
1. Be helpful, informative, and transparent
2. Mention security features when relevant to the conversation
3. Keep responses concise but comprehensive
4. If asked about security, explain SHA-256 hashing
5. Always acknowledge when a conversation is being secured

Remember: All messages are hashed with SHA-256 for verification."""
        
        start_time = time.time()
        
        # Generate response
        response = model.generate_content(
            f"{system_prompt}\n\nUser: {user_message}\nNeuralSync:",
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=500,
                top_p=0.9,
                top_k=40
            )
        )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Estimate token usage (Gemini doesn't provide exact token count in response)
        estimated_tokens = len(response.text.split()) * 1.3  # Rough estimate
        
        return {
            'text': response.text.strip(),
            'response_time_ms': response_time_ms,
            'tokens_used': int(estimated_tokens),
            'model': 'gemini-pro'
        }
        
    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        raise

# Local fallback responses
def get_local_response(user_message):
    """Generate local fallback responses if API fails"""
    user_message_lower = user_message.lower()
    
    responses = {
        'hello': "Hello! I'm NeuralSync, your transparent AI assistant. How can I help you today?",
        'hi': "Hi there! Ready to have a secure conversation?",
        'how are you': "I'm functioning optimally! As an AI, I don't have feelings, but I'm ready to assist you.",
        'what can you do': "I can have conversations, answer questions, help with tasks, and everything is securely hashed with SHA-256 for transparency!",
        'security': "Every message is cryptographically hashed using SHA-256. This creates a unique fingerprint for each conversation that can be independently verified to ensure no tampering has occurred.",
        'privacy': "Your privacy is important. All conversations are hashed and stored securely. You have full control over your data.",
        'help': "I'm here to help! You can ask me anything, and our conversation will be transparently logged and secured with SHA-256 hashing.",
        'features': "NeuralSync offers: 1) Cryptographic message verification 2) Complete conversation history 3) Real-time analytics 4) Transparent AI interactions 5) Secure data storage",
        'about': "NeuralSync is a transparent AI platform that uses blockchain-inspired cryptography (SHA-256) for verifiable conversations.",
        'dashboard': "Check your dashboard for conversation analytics, activity charts, and usage statistics.",
        'history': "Your complete chat history is available with timestamps and cryptographic hashes for verification.",
        'sha256': "SHA-256 is a cryptographic hash function that produces a 256-bit (64-character) hash value. It's used to create unique fingerprints for our conversations, ensuring integrity and transparency.",
        'verify': "You can verify any message by checking its SHA-256 hash. This ensures the conversation hasn't been modified.",
        'code': "NeuralSync is built with Python Flask, uses SQLite for storage, and implements SHA-256 hashing for all messages.",
        'default': f"I understand you're asking about '{user_message}'. As a transparent AI assistant, I want to acknowledge that this message will be cryptographically hashed with SHA-256 for verification. This ensures our conversation remains tamper-proof and verifiable."
    }
    
    # Check for keywords
    for keyword, response in responses.items():
        if keyword in user_message_lower:
            return {
                'text': response,
                'response_time_ms': 100,
                'tokens_used': len(response.split()),
                'model': 'local-fallback'
            }
    
    # Default response
    return {
        'text': responses['default'],
        'response_time_ms': 50,
        'tokens_used': len(responses['default'].split()),
        'model': 'local-fallback'
    }

# Main bot response function
def get_bot_response(user_message):
    """Get bot response, trying Gemini first then falling back to local"""
    # Clean and validate input
    user_message = user_message.strip()
    if not user_message or len(user_message) < 1:
        return get_local_response("empty")
    
    try:
        # Try Gemini API first
        if GEMINI_API_KEY:
            return get_gemini_response(user_message)
        else:
            return get_local_response(user_message)
    except Exception as e:
        logger.warning(f"Falling back to local response due to: {e}")
        return get_local_response(user_message)

# Session management middleware
@app.before_request
def manage_session():
    """Manage user sessions"""
    if 'user_id' not in session:
        session['user_id'] = hashlib.sha256(str(datetime.now().timestamp()).encode()).hexdigest()[:16]
        session['session_start'] = datetime.now().isoformat()
    
    # Generate session cookie if not present
    if not request.cookies.get('session_id'):
        resp = make_response()
        resp.set_cookie('session_id', session['user_id'], max_age=timedelta(days=7))
        return resp

# Routes
@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/chat')
def chat():
    """Chat page"""
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
@rate_limit(max_requests=20, window=60)
def api_chat():
    """API endpoint for chat messages"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        user_message = data.get('message', '').strip()
        session_id = request.cookies.get('session_id', session.get('user_id', 'default_session'))
        
        if not user_message:
            return jsonify({'error': 'Empty message'}), 400
        
        if len(user_message) > 2000:
            return jsonify({'error': 'Message too long (max 2000 characters)'}), 400
        
        logger.info(f"Processing message from session {session_id[:8]}: {user_message[:50]}...")
        
        # Generate bot response
        bot_data = get_bot_response(user_message)
        
        # Save to database
        chat_info = save_chat(
            session_id, 
            user_message, 
            bot_data['text'],
            response_time_ms=bot_data['response_time_ms'],
            tokens_used=bot_data['tokens_used']
        )
        
        if not chat_info:
            return jsonify({'error': 'Failed to save chat'}), 500
        
        return jsonify({
            'success': True,
            'user_message': user_message,
            'bot_response': bot_data['text'],
            'timestamp': chat_info['timestamp'],
            'hash': chat_info['hash'],
            'short_hash': chat_info['hash'][:16] + '...',
            'response_time': f"{bot_data['response_time_ms']}ms",
            'model_used': bot_data['model'],
            'tokens_used': bot_data['tokens_used']
        })
        
    except Exception as e:
        logger.error(f"API chat error: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/dashboard')
def dashboard():
    """Dashboard page with analytics"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Total messages
        cursor.execute('SELECT COUNT(*) FROM chat_history')
        total_messages = cursor.fetchone()[0] or 0
        
        # Active sessions today
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT COUNT(DISTINCT session_id) FROM chat_history WHERE DATE(timestamp) = ?', (today,))
        active_today = cursor.fetchone()[0] or 0
        
        # Average response time
        cursor.execute('SELECT AVG(response_time_ms) FROM chat_history WHERE response_time_ms > 0')
        avg_response_raw = cursor.fetchone()[0] or 100
        avg_response = f"{avg_response_raw:.1f}ms"
        
        # Security status
        security_status = "SHA-256 Active ✓"
        
        # Total tokens used (if using API)
        cursor.execute('SELECT SUM(tokens_used) FROM chat_history')
        total_tokens = cursor.fetchone()[0] or 0
        
        # Recent activity (last 10)
        cursor.execute('''
            SELECT id, user_message, bot_response, timestamp, message_hash
            FROM chat_history
            ORDER BY id DESC
            LIMIT 10
        ''')
        recent_activity = cursor.fetchall()
        
        # Messages per day (last 7 days)
        cursor.execute('''
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM chat_history
            WHERE DATE(timestamp) >= DATE('now', '-7 days')
            GROUP BY DATE(timestamp)
            ORDER BY date ASC
        ''')
        daily_stats = cursor.fetchall()
        
        # If no data, create sample data for demo
        if not daily_stats:
            daily_stats = []
            for i in range(7):
                date = (datetime.now() - timedelta(days=6-i)).strftime('%Y-%m-%d')
                count = max(1, (total_messages // 7) + (i % 3))
                daily_stats.append((date, count))
        
        conn.close()
        
        stats = {
            'total_messages': total_messages,
            'active_today': active_today,
            'avg_response': avg_response,
            'security_status': security_status,
            'total_tokens': f"{total_tokens:,}",
            'recent_activity': recent_activity,
            'daily_stats': daily_stats,
            'api_configured': bool(GEMINI_API_KEY)
        }
        
        return render_template('dashboard.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return render_template('dashboard.html', stats={})

@app.route('/history')
def history():
    """Chat history page"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Get session ID for filtering
        session_id = request.cookies.get('session_id', '')
        
        # Fetch all chats with pagination
        page = request.args.get('page', 1, type=int)
        per_page = 10
        offset = (page - 1) * per_page
        
        # Build query based on session
        if session_id and session_id != 'default_session':
            cursor.execute('SELECT COUNT(*) FROM chat_history WHERE session_id = ?', (session_id,))
            total_chats = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT id, user_message, bot_response, timestamp, message_hash
                FROM chat_history
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            ''', (session_id, per_page, offset))
        else:
            cursor.execute('SELECT COUNT(*) FROM chat_history')
            total_chats = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT id, user_message, bot_response, timestamp, message_hash
                FROM chat_history
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            ''', (per_page, offset))
        
        chats = cursor.fetchall()
        total_pages = max(1, (total_chats + per_page - 1) // per_page)
        
        conn.close()
        
        return render_template('history.html', 
                             chats=chats, 
                             page=page, 
                             total_pages=total_pages,
                             total_chats=total_chats,
                             session_id=session_id[:8] if session_id else '')
        
    except Exception as e:
        logger.error(f"History error: {e}")
        return render_template('history.html', chats=[], page=1, total_pages=1, total_chats=0)

@app.route('/api/verify', methods=['POST'])
def verify_message():
    """API endpoint to verify message integrity"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        message_id = data.get('id')
        expected_hash = data.get('hash')
        
        if not message_id or not expected_hash:
            return jsonify({'error': 'Missing id or hash'}), 400
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_message, bot_response, timestamp, message_hash
            FROM chat_history
            WHERE id = ?
        ''', (message_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'verified': False, 'error': 'Message not found'}), 404
        
        user_message, bot_response, timestamp, stored_hash = result
        
        # Regenerate hash
        recalculated_hash = generate_hash(user_message, bot_response, timestamp)
        
        verified = recalculated_hash == stored_hash == expected_hash
        
        return jsonify({
            'verified': verified,
            'stored_hash': stored_hash,
            'recalculated_hash': recalculated_hash,
            'message_id': message_id,
            'message': '✓ Hash verification successful - Message integrity confirmed' if verified else '✗ Hash mismatch detected - Message may have been tampered with'
        })
        
    except Exception as e:
        logger.error(f"Verify error: {e}")
        return jsonify({'verified': False, 'error': str(e)}), 500

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@app.route('/privacy')
def privacy():
    """Privacy policy page"""
    return render_template('privacy.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()
        
        # Simple validation
        if not name or not email or not message:
            return render_template('contact.html', error='All fields are required')
        
        if '@' not in email or '.' not in email:
            return render_template('contact.html', error='Please enter a valid email address')
        
        # In a real app, save to database and send email
        success_data = {
            'success': True,
            'message': 'Thank you for your message! We\'ll get back to you soon.',
            'submitted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return render_template('contact.html', success=success_data)
    
    return render_template('contact.html')

@app.route('/api/analytics')
def get_analytics():
    """API endpoint for real-time analytics"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Get hourly activity for today
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
            FROM chat_history
            WHERE DATE(timestamp) = ?
            GROUP BY strftime('%H', timestamp)
            ORDER BY hour
        ''', (today,))
        
        hourly_data = cursor.fetchall()
        
        # Get daily activity for last 30 days
        cursor.execute('''
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM chat_history
            WHERE DATE(timestamp) >= DATE('now', '-30 days')
            GROUP BY DATE(timestamp)
            ORDER BY date
        ''')
        daily_data = cursor.fetchall()
        
        # Get top conversation topics
        cursor.execute('''
            SELECT user_message FROM chat_history
            WHERE DATE(timestamp) >= DATE('now', '-7 days')
            ORDER BY id DESC
            LIMIT 100
        ''')
        recent_messages = [row[0] for row in cursor.fetchall()]
        
        # Simple topic analysis
        topics = {}
        keywords = {
            'help': ['help', 'assist', 'support', 'how to', 'guide'],
            'security': ['security', 'sha256', 'hash', 'encrypt', 'secure'],
            'technical': ['python', 'code', 'api', 'github', 'technical', 'develop'],
            'general': ['hello', 'hi', 'hey', 'good morning', 'good evening'],
            'features': ['feature', 'what can', 'capability', 'function'],
            'about': ['about', 'what is', 'who are', 'tell me about']
        }
        
        for category, words in keywords.items():
            count = sum(1 for msg in recent_messages if any(word in msg.lower() for word in words))
            if count > 0:
                topics[category] = count
        
        conn.close()
        
        return jsonify({
            'hourly_activity': [{'hour': h, 'count': c} for h, c in hourly_data],
            'daily_activity': [{'date': d, 'count': c} for d, c in daily_data],
            'topics': topics,
            'total_conversations': sum(c for _, c in daily_data),
            'api_available': bool(GEMINI_API_KEY),
            'updated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recent-messages')
def get_recent_messages():
    """Get recent chat messages for current session"""
    try:
        session_id = request.cookies.get('session_id', session.get('user_id', 'default_session'))
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        limit = request.args.get('limit', 5, type=int)
        
        cursor.execute('''
            SELECT id, user_message, bot_response, message_hash, timestamp
            FROM chat_history
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
        ''', (session_id, limit))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'id': row[0],
                'user_message': row[1],
                'bot_response': row[2],
                'message_hash': row[3],
                'timestamp': row[4]
            })
        
        conn.close()
        return jsonify(messages)
        
    except Exception as e:
        logger.error(f"Recent messages error: {e}")
        return jsonify([])

@app.route('/api/session')
def get_session_info():
    """Get session information"""
    try:
        session_id = request.cookies.get('session_id', session.get('user_id', None))
        
        if not session_id:
            # Generate new session ID
            session_id = hashlib.sha256(str(datetime.now().timestamp()).encode()).hexdigest()[:16]
            response = make_response(jsonify({'session_id': session_id, 'new_session': True}))
            response.set_cookie('session_id', session_id, max_age=timedelta(days=7))
            return response
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT message_count, created_at, last_activity, total_tokens
            FROM user_sessions
            WHERE session_id = ?
        ''', (session_id,))
        
        session_data = cursor.fetchone()
        
        if not session_data:
            # Create new session
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO user_sessions (session_id, created_at, last_activity, message_count, total_tokens)
                VALUES (?, ?, ?, 0, 0)
            ''', (session_id, created_at, created_at))
            conn.commit()
            session_data = (0, created_at, created_at, 0)
        
        conn.close()
        
        return jsonify({
            'session_id': session_id,
            'message_count': session_data[0],
            'created_at': session_data[1],
            'last_activity': session_data[2],
            'total_tokens': session_data[3],
            'api_configured': bool(GEMINI_API_KEY)
        })
        
    except Exception as e:
        logger.error(f"Session info error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'api_configured': bool(GEMINI_API_KEY),
        'database': 'connected' if os.path.exists('database.db') else 'not_found'
    })

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404

@app.errorhandler(429)
def ratelimit_handler(error):
    """Handle rate limit errors"""
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': 'Please wait a moment before sending more messages'
    }), 429

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# Static file serving with cache control
@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files with cache control"""
    response = send_from_directory('static', filename)
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Create some sample data for demo if needed
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM chat_history')
    if cursor.fetchone()[0] == 0:
        logger.info("Creating sample conversations...")
        sample_conversations = [
            ("Hello, how are you?", "Hello! I'm NeuralSync, your transparent AI assistant. I'm functioning optimally and ready to help!"),
            ("What is SHA-256 security?", "SHA-256 is a cryptographic hash function that generates a unique 256-bit hash for each conversation, ensuring data integrity and transparency."),
            ("Can I verify my chat history?", "Yes! Every message is hashed with SHA-256. You can verify any conversation in your history using the provided hash."),
            ("What makes NeuralSync different?", "Unlike traditional chatbots, NeuralSync provides complete transparency with cryptographic verification for every conversation."),
            ("How do I view my analytics?", "Visit your dashboard to see real-time analytics, conversation patterns, and usage statistics.")
        ]
        for user_msg, bot_resp in sample_conversations:
            save_chat('demo_session', user_msg, bot_resp)
    conn.close()
    
    logger.info("Starting NeuralSync server...")
    app.run(debug=True, host='127.0.0.1', port=5000)