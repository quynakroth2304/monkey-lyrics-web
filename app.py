from flask import Flask, render_template, request, jsonify
import syncedlyrics
import google.generativeai as genai
import os
import psycopg2
import yt_dlp
import re

app = Flask(__name__)

# --- CẤU HÌNH API GEMINI ---
GEMINI_API_KEY = os.environ.get("AIzaSyCVSjO8txkpPYSC7IiPAjdi9kHzDM-CooA")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro')

# --- KẾT NỐI DATABASE (POSTGRES) ---
def get_db_connection():
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not db_url: raise Exception("Chưa cấu hình Database URL!")
    conn = psycopg2.connect(db_url)
    return conn

# --- INIT DB (Tạo bảng nếu chưa có) ---
def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (username VARCHAR(50) PRIMARY KEY, password VARCHAR(100) NOT NULL);
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                id SERIAL PRIMARY KEY, username VARCHAR(50), title VARCHAR(200), lrc TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cur.close(); conn.close()
    except Exception as e: print(f"DB Error: {e}")

init_db()

@app.route('/')
def index(): return render_template('index.html')

# --- API AUTH (Giữ nguyên) ---
@app.route('/api/auth', methods=['POST'])
def auth():
    data = request.json
    action = data.get('action'); username = data.get('username').lower().strip(); password = data.get('password')
    try:
        conn = get_db_connection(); cur = conn.cursor()
        if action == 'register':
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cur.fetchone(): return jsonify({'error': 'Tên trùng rồi!'}), 400
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            conn.commit(); return jsonify({'success': True, 'msg': 'Đăng ký thành công!'})
        elif action == 'login':
            cur.execute("SELECT password FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            if user and user[0] == password: return jsonify({'success': True, 'msg': 'Login OK!'})
            else: return jsonify({'error': 'Sai mật khẩu!'}), 401
        cur.close(); conn.close()
    except Exception as e: return jsonify({'error': str(e)}), 500

# --- API XỬ LÝ LINK & TÌM NHẠC (NÂNG CẤP) ---
@app.route('/get-song', methods=['POST'])
def get_song():
    data = request.json
    song_input = data.get('query')
    username = data.get('username')
    
    if not song_input: return jsonify({'error': 'Nhập gì đó đi!'}), 400

    title_to_search = song_input

    try:
        # 1. KIỂM TRA XEM CÓ PHẢI LINK KHÔNG
        if song_input.startswith(('http://', 'https://')):
            print(f"🔗 Phát hiện Link: {song_input}")
            # Dùng yt-dlp để lấy tên bài hát (KHÔNG TẢI VIDEO)
            ydl_opts = {
                'quiet': True,
                'skip_download': True, # Chỉ lấy thông tin
                'extract_flat': True,  # Chế độ siêu nhanh
                'noplaylist': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(song_input, download=False)
                raw_title = info.get('title', 'Unknown Song')
                
                # Làm sạch tên (Bỏ Official MV, Lyrics, 4K...) để tìm lời cho chuẩn
                clean_title = re.sub(r"[\(\[].*?[\)\]]", "", raw_title) # Bỏ ngoặc (...)
                clean_title = clean_title.split('|')[0].strip() # Bỏ phần sau dấu |
                clean_title = clean_title.split('-')[1].strip() if '-' in clean_title else clean_title # Ưu tiên lấy phần Tên bài sau dấu gạch ngang (nếu có)
                
                print(f"Title gốc: {raw_title} -> Tìm kiếm: {clean_title}")
                title_to_search = clean_title
        
        # 2. TÌM LỜI BÀI HÁT
        print(f"🔎 Đang tìm lời cho: {title_to_search}")
        lrc_content = syncedlyrics.search(title_to_search)
        
        if not lrc_content:
            # Fallback: Thử tìm bằng tên gốc nếu tên sạch ko ra
            lrc_content = syncedlyrics.search(song_input) if not song_input.startswith('http') else None

        if not lrc_content:
            return jsonify({'error': f'Không tìm thấy lời cho: {title_to_search}'}), 404
        
        final_title = title_to_search.upper()

        # 3. LƯU VÀO DATABASE (SQL)
        if username:
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute("SELECT id FROM songs WHERE username = %s AND title = %s", (username, final_title))
            if not cur.fetchone():
                cur.execute("INSERT INTO songs (username, title, lrc) VALUES (%s, %s, %s)", (username, final_title, lrc_content))
                conn.commit()
            cur.close(); conn.close()

        return jsonify({'title': final_title, 'lrc': lrc_content})

    except Exception as e:
        print(f"Lỗi: {e}")
        return jsonify({'error': 'Lỗi xử lý Link (Có thể do mạng hoặc link hỏng)'}), 500

# --- API MY SONGS ---
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

@app.route('/analyze-lyrics', methods=['POST'])
def analyze_lyrics():
    # ... (Giữ nguyên code Gemini cũ của bạn)
    return jsonify({'error': 'Gemini function'}) 

if __name__ == '__main__':
    app.run(debug=True, port=5000)