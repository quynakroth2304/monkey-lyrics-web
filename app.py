from flask import Flask, render_template, request, jsonify
import syncedlyrics
import google.generativeai as genai
import os
import yt_dlp
import re
import requests

app = Flask(__name__)

# --- CẤU HÌNH API GEMINI ---
GEMINI_API_KEY = os.environ.get("AIzaSyCVSjO8txkpPYSC7IiPAjdi9kHzDM-CooA")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro')

@app.route('/')
def index():
    return render_template('index.html')

# --- 1. TÌM LIST BÀI HÁT ---
@app.route('/search-list', methods=['POST'])
def search_list():
    query = request.json.get('query')
    if not query: return jsonify({'error': 'Nhập tên bài đi!'}), 400
    try:
        ydl_opts = {'quiet': True, 'extract_flat': True, 'noplaylist': True, 'limit': 5}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch5:{query}", download=False)
            entries = info.get('entries', [])
            return jsonify([{'title': i['title'], 'id': i['id']} for i in entries])
    except Exception as e: return jsonify({'error': str(e)}), 500

# --- 2. LẤY LỜI BÀI HÁT ---
@app.route('/get-lyrics', methods=['POST'])
def get_lyrics():
    data = request.json
    title = data.get('title')
    try:
        clean_title = re.sub(r"[\(\[].*?[\)\]]", "", title).strip()
        lrc = syncedlyrics.search(clean_title)
        if not lrc: lrc = syncedlyrics.search(title)
        if not lrc: return jsonify({'error': 'Không tìm thấy lời!'}), 404
        return jsonify({'title': title, 'lrc': lrc})
    except Exception as e: return jsonify({'error': str(e)}), 500

# --- 3. AI TỰ VIẾT VĂN MẪU (NEW UPDATE) ---
@app.route('/get-quote', methods=['POST'])
def get_quote():
    # Lấy độ dài người dùng chọn (30, 50, 100...)
    length = int(request.json.get('length', 50))
    
    try:
        # Prompt ra lệnh cho Gemini viết văn
        prompt = f"""
        Hãy đóng vai một nhà văn Việt Nam. Viết một đoạn văn xuôi ngẫu nhiên, giàu cảm xúc và ý nghĩa.
        Chủ đề: Cuộc sống, Tuổi trẻ, Tình yêu quê hương, hoặc Hà Nội/Sài Gòn xưa.
        Độ dài yêu cầu: Khoảng {length} từ (hãy viết gần đúng số lượng này).
        
        QUAN TRỌNG: 
        1. Chỉ trả về nội dung văn bản thuần túy.
        2. Không có tiêu đề, không có dấu ngoặc kép bao quanh.
        3. Văn phong phải mượt mà, đúng chính tả tiếng Việt.
        """
        
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Xử lý sạch văn bản nếu AI lỡ thêm markdown
        content = content.replace('*', '').replace('#', '').replace('"', '')
        
        return jsonify({'content': content, 'author': 'Gemini Sáng Tác'})

    except Exception as e:
        print(f"AI Error: {e}")
        # Fallback nếu AI bị lỗi hoặc hết quota thì dùng tạm câu này
        return jsonify({
            'content': "Đời người như một dòng sông, lững lờ trôi qua bao ghềnh thác để rồi hòa mình vào biển lớn mênh mông. Sống là phải biết yêu thương và sẻ chia.", 
            'author': 'System Fallback'
        })

if __name__ == '__main__':
    app.run(debug=True, port=5000)