from flask import Flask, render_template, request, jsonify
import syncedlyrics
import google.generativeai as genai
import os
import yt_dlp
import re

app = Flask(__name__)

# --- CẤU HÌNH API GEMINI ---
# Lấy key từ biến môi trường trên Vercel
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro')

@app.route('/')
def index():
    return render_template('index.html')

# --- 1. TÌM DANH SÁCH BÀI HÁT (HIỆN 5 BÀI) ---
@app.route('/search-list', methods=['POST'])
def search_list():
    query = request.json.get('query')
    if not query: return jsonify({'error': 'Nhập tên bài đi bạn ơi!'}), 400
    
    try:
        # Cấu hình yt-dlp tìm nhanh, không tải video
        ydl_opts = {
            'quiet': True,
            'extract_flat': True, # Chỉ lấy thông tin cơ bản
            'noplaylist': True,
            'limit': 5 # Lấy 5 kết quả
        }
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
    except Exception as e:
        print(f"Lỗi tìm kiếm: {e}")
        return jsonify({'error': 'Lỗi khi tìm bài hát.'}), 500

# --- 2. LẤY LỜI BÀI HÁT ---
@app.route('/get-lyrics', methods=['POST'])
def get_lyrics():
    data = request.json
    title = data.get('title') # Đây có thể là tên bài hoặc Link
    
    try:
        clean_title = title

        # Nếu là Link Youtube -> Lấy tên bài gốc trước
        if title.startswith(('http://', 'https://')):
            ydl_opts = {'quiet': True, 'skip_download': True, 'noplaylist': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(title, download=False)
                clean_title = info.get('title', 'Unknown Song')

        # Làm sạch tên (Bỏ Official, 4K...) để dễ tìm lời
        clean_title = re.sub(r"[\(\[].*?[\)\]]", "", clean_title)
        clean_title = clean_title.split('|')[0].strip()
        
        print(f"Đang tìm lời cho: {clean_title}")
        lrc = syncedlyrics.search(clean_title)
        
        # Nếu không thấy thì tìm bằng tên gốc
        if not lrc and clean_title != title:
            lrc = syncedlyrics.search(title)
        
        if not lrc: 
            return jsonify({'error': 'Không tìm thấy lời bài này!'}), 404
            
        return jsonify({'title': clean_title, 'lrc': lrc})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- 3. AI VIẾT VĂN MẪU (Theo độ dài từ) ---
@app.route('/get-quote', methods=['POST'])
def get_quote():
    # Lấy độ dài người dùng chọn (30, 50, 100...)
    length = int(request.json.get('length', 50))
    
    try:
        if not GEMINI_API_KEY:
            return jsonify({'content': "Chưa cấu hình Gemini API Key nên không viết văn được.", 'author': "System"})

        prompt = f"""
        Đóng vai một nhà văn Việt Nam. Hãy viết một đoạn văn xuôi giàu cảm xúc.
        Chủ đề ngẫu nhiên: Tuổi trẻ, Quê hương, Tình yêu, Cuộc sống, hoặc Hà Nội/Sài Gòn xưa.
        Độ dài: Khoảng {length} từ.
        Yêu cầu: Chỉ trả về nội dung văn bản thuần túy, không có tiêu đề, không markdown.
        """
        
        response = model.generate_content(prompt)
        content = response.text.strip().replace('*', '').replace('#', '').replace('"', '')
        
        return jsonify({'content': content, 'author': 'Gemini AI Sáng Tác'})

    except Exception as e:
        print(f"Lỗi AI: {e}")
        return jsonify({'content': "Không thể kết nối với AI lúc này. Hãy thử lại sau.", 'author': "Error"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)