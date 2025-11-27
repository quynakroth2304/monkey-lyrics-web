from flask import Flask, render_template, request, jsonify
import syncedlyrics
import google.generativeai as genai
import os
import psycopg2
import yt_dlp
import re
import requests
import random

app = Flask(__name__)

# --- CẤU HÌNH ---
GEMINI_API_KEY = os.environ.get("AIzaSyCVSjO8txkpPYSC7IiPAjdi9kHzDM-CooA")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro')

def get_db_connection():
    db_url = os.environ.get("postgresql://neondb_owner:npg_CfJR2LVcpg4M@ep-shiny-moon-a1uohyjc-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require") or os.environ.get("postgresql://neondb_owner:npg_CfJR2LVcpg4M@ep-shiny-moon-a1uohyjc-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require")
    if not db_url: raise Exception("Chưa cấu hình Database URL!")
    conn = psycopg2.connect(db_url)
    return conn

# --- INIT DB ---
def init_db():
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS users (username VARCHAR(50) PRIMARY KEY, password VARCHAR(100) NOT NULL);")
        cur.execute("CREATE TABLE IF NOT EXISTS songs (id SERIAL PRIMARY KEY, username VARCHAR(50), title VARCHAR(200), lrc TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
        conn.commit(); cur.close(); conn.close()
    except Exception as e: print(f"DB Error: {e}")

init_db()

@app.route('/')
def index(): return render_template('index.html')

# --- AUTH ---
@app.route('/api/auth', methods=['POST'])
def auth():
    data = request.json
    action = data.get('action'); u = data.get('username').lower().strip(); p = data.get('password')
    try:
        conn = get_db_connection(); cur = conn.cursor()
        if action == 'register':
            cur.execute("SELECT * FROM users WHERE username = %s", (u,))
            if cur.fetchone(): return jsonify({'error': 'Tên trùng!'}), 400
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (u, p))
            conn.commit(); return jsonify({'success': True, 'msg': 'Đăng ký xong!'})
        elif action == 'login':
            cur.execute("SELECT password FROM users WHERE username = %s", (u,))
            user = cur.fetchone()
            if user and user[0] == p: return jsonify({'success': True, 'msg': 'Login OK!'})
            else: return jsonify({'error': 'Sai mật khẩu!'}), 401
        cur.close(); conn.close()
    except Exception as e: return jsonify({'error': str(e)}), 500

# --- TÍNH NĂNG 1: TÌM LIST BÀI HÁT (YT-DLP) ---
@app.route('/search-list', methods=['POST'])
def search_list():
    query = request.json.get('query')
    if not query: return jsonify({'error': 'Nhập tên bài đi!'}), 400
    
    try:
        # Tìm 5 kết quả đầu tiên trên Youtube
        ydl_opts = {'quiet': True, 'extract_flat': True, 'noplaylist': True, 'limit': 5}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch5:{query}", download=False)
            entries = info.get('entries', [])
            
            results = []
            for item in entries:
                results.append({
                    'title': item['title'],
                    'id': item['id'],
                    'duration': item.get('duration')
                })
            return jsonify(results)
    except Exception as e: return jsonify({'error': str(e)}), 500

# --- TÍNH NĂNG 2: LẤY LỜI BÀI HÁT CHÍNH XÁC ---
@app.route('/get-lyrics', methods=['POST'])
def get_lyrics():
    data = request.json
    title = data.get('title')
    username = data.get('username')
    
    try:
        # Làm sạch tên bài hát
        clean_title = re.sub(r"[\(\[].*?[\)\]]", "", title).strip()
        
        lrc = syncedlyrics.search(clean_title)
        if not lrc: lrc = syncedlyrics.search(title) # Fallback
        
        if not lrc: return jsonify({'error': 'Không tìm thấy lời!'}), 404
        
        # Lưu vào DB
        if username:
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute("SELECT id FROM songs WHERE username = %s AND title = %s", (username, title))
            if not cur.fetchone():
                cur.execute("INSERT INTO songs (username, title, lrc) VALUES (%s, %s, %s)", (username, title, lrc))
                conn.commit()
            cur.close(); conn.close()
            
        return jsonify({'title': title, 'lrc': lrc})
    except Exception as e: return jsonify({'error': str(e)}), 500

# --- TÍNH NĂNG 3: LẤY TRÍCH DẪN NGẪU NHIÊN ---
@app.route('/get-quote', methods=['GET'])
def get_quote():
    try:
        # Gọi API Quotable để lấy câu nói tiếng Anh
        r = requests.get("https://api.quotable.io/random?minLength=100")
        if r.status_code == 200:
            data = r.json()
            return jsonify({'content': data['content'], 'author': data['author']})
        else:
            # Fallback nếu API lỗi
            return jsonify({'content': "Success is not final, failure is not fatal: it is the courage to continue that counts.", 'author': "Winston Churchill"})
    except:
        return jsonify({'content': "The only way to do great work is to love what you do.", 'author': "Steve Jobs"})

# --- API LẤY BÀI ĐÃ LƯU ---
@app.route('/api/my-songs', methods=['POST'])
def my_songs():
    username = request.json.get('username')
    if not username: return jsonify([])
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute("SELECT title, lrc FROM songs WHERE username = %s ORDER BY created_at DESC", (username,))
        rows = cur.fetchall()
        cur.close(); conn.close()
        return jsonify([{'title': r[0], 'lrc': r[1]} for r in rows])
    except: return jsonify([])

if __name__ == '__main__':
    app.run(debug=True, port=5000)