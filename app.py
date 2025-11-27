from flask import Flask, render_template, request, jsonify
import syncedlyrics
import google.generativeai as genai
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# --- 1. CẤU HÌNH API GEMINI ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro')

# --- 2. CẤU HÌNH FIREBASE (DATABASE) ---
firebase_key_json = os.environ.get("FIREBASE_KEY")
db = None

if firebase_key_json:
    try:
        cred_dict = json.loads(firebase_key_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("🔥 Firebase Connected!")
    except Exception as e:
        print(f"⚠️ Firebase Error: {e}")

@app.route('/')
def index():
    return render_template('index.html')

# --- API: ĐĂNG KÝ / ĐĂNG NHẬP ---
@app.route('/api/auth', methods=['POST'])
def auth():
    if not db: return jsonify({'error': 'Chưa kết nối Database!'}), 500
    data = request.json
    action = data.get('action')
    username = data.get('username').lower().strip()
    password = data.get('password')

    users_ref = db.collection('users')
    
    try:
        if action == 'register':
            if users_ref.document(username).get().exists:
                return jsonify({'error': 'Tên này có người lấy rồi!'}), 400
            
            users_ref.document(username).set({
                'password': password,
                'created_at': firestore.SERVER_TIMESTAMP
            })
            return jsonify({'success': True, 'msg': 'Đăng ký thành công! Login đi.'})

        elif action == 'login':
            doc = users_ref.document(username).get()
            if not doc.exists: return jsonify({'error': 'Tài khoản không tồn tại!'}), 404
            
            user_data = doc.to_dict()
            if user_data['password'] == password:
                return jsonify({'success': True, 'msg': 'Login ngon lành!'})
            else:
                return jsonify({'error': 'Sai mật khẩu!'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- API: LẤY DANH SÁCH BÀI HÁT ĐÃ LƯU ---
@app.route('/api/my-songs', methods=['POST'])
def my_songs():
    if not db: return jsonify([]), 200
    username = request.json.get('username')
    if not username: return jsonify([]), 200

    try:
        songs_ref = db.collection('users').document(username).collection('songs')
        docs = songs_ref.stream() # Lấy danh sách
        song_list = [{'title': d.id, 'lrc': d.to_dict()['lrc']} for d in docs]
        return jsonify(song_list)
    except:
        return jsonify([])

# --- API: TÌM NHẠC MỚI & LƯU TỰ ĐỘNG ---
@app.route('/get-song', methods=['POST'])
def get_song():
    data = request.json
    song_input = data.get('query')
    username = data.get('username')

    if not song_input: return jsonify({'error': 'Nhập tên bài đi!'}), 400

    try:
        # Tìm lời bài hát
        lrc_content = syncedlyrics.search(song_input)
        if not lrc_content: return jsonify({'error': 'Không tìm thấy lời bài này!'}), 404
        
        title = song_input.upper() # Dùng tên người dùng nhập làm ID luôn

        # Lưu vào Firebase nếu đã đăng nhập
        if db and username:
            db.collection('users').document(username).collection('songs').document(title).set({
                'lrc': lrc_content,
                'saved_at': firestore.SERVER_TIMESTAMP
            })

        return jsonify({'title': title, 'lrc': lrc_content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)