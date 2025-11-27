from flask import Flask, render_template, request, jsonify
import syncedlyrics
import google.generativeai as genai
import os
import yt_dlp
import re
import requests

app = Flask(__name__)

# --- CẤU HÌNH API GEMINI (Giữ nguyên nếu bạn dùng) ---
GEMINI_API_KEY = os.environ.get("AIzaSyCVSjO8txkpPYSC7IiPAjdi9kHzDM-CooA")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro')

@app.route('/')
def index():
    return render_template('index.html')

# --- 1. TÌM LIST BÀI HÁT (Hiện 5 bài để chọn) ---
@app.route('/search-list', methods=['POST'])
def search_list():
    query = request.json.get('query')
    if not query: return jsonify({'error': 'Nhập tên bài đi!'}), 400
    
    try:
        # Tìm 5 kết quả đầu tiên trên Youtube (Siêu nhanh, ko tải video)
        ydl_opts = {'quiet': True, 'extract_flat': True, 'noplaylist': True, 'limit': 5}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch5:{query}", download=False)
            entries = info.get('entries', [])
            
            results = []
            for item in entries:
                results.append({
                    'title': item['title'],
                    'id': item['id']
                })
            return jsonify(results)
    except Exception as e: return jsonify({'error': str(e)}), 500

# --- 2. LẤY LỜI BÀI HÁT CHÍNH XÁC ---
@app.route('/get-lyrics', methods=['POST'])
def get_lyrics():
    data = request.json
    title = data.get('title')
    
    try:
        # Làm sạch tên bài hát (Bỏ Official MV, 4K...) để tìm lời chuẩn hơn
        clean_title = re.sub(r"[\(\[].*?[\)\]]", "", title).strip()
        
        print(f"Finding lyrics for: {clean_title}")
        lrc = syncedlyrics.search(clean_title)
        
        # Nếu tìm bằng tên sạch không ra thì tìm bằng tên gốc
        if not lrc: lrc = syncedlyrics.search(title)
        
        if not lrc: return jsonify({'error': 'Không tìm thấy lời bài này!'}), 404
            
        return jsonify({'title': title, 'lrc': lrc})
    except Exception as e: return jsonify({'error': str(e)}), 500

# --- 3. LẤY TRÍCH DẪN NGẪU NHIÊN (QUOTE) ---
@app.route('/get-quote', methods=['GET'])
def get_quote():
    try:
        # Lấy quote tiếng Anh ngẫu nhiên
        r = requests.get("https://api.quotable.io/random?minLength=100")
        if r.status_code == 200:
            data = r.json()
            return jsonify({'content': data['content'], 'author': data['author']})
        else:
            return jsonify({'content': "Success is not final, failure is not fatal: it is the courage to continue that counts.", 'author': "Winston Churchill"})
    except:
        return jsonify({'content': "The only way to do great work is to love what you do.", 'author': "Steve Jobs"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)