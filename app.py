from flask import Flask, render_template, request, jsonify
import syncedlyrics
import google.generativeai as genai
import os

app = Flask(__name__)

# --- CẤU HÌNH API GEMINI ---
# Lấy API Key từ biến môi trường trên Vercel
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Nếu chạy local (trên máy) mà chưa set biến môi trường thì điền key vào đây để test
# GEMINI_API_KEY = "DÁN_KEY_CỦA_BẠN_VÀO_ĐÂY_NẾU_CHẠY_MÁY_NHÀ"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-song', methods=['POST'])
def get_song():
    data = request.json
    song_input = data.get('query')
    
    if not song_input:
        return jsonify({'error': 'Nhập tên bài hát đi bạn ơi!'}), 400

    try:
        print(f"--- Đang tìm lời cho: {song_input} ---")
        
        # LOGIC MỚI: BỎ QUA YOUTUBE, TÌM TRỰC TIẾP LỜI
        # syncedlyrics sẽ tự tìm trên Musixmatch, Spotify...
        lrc_content = syncedlyrics.search(song_input)
        
        if not lrc_content:
            return jsonify({'error': 'Không tìm thấy lời bài này. Thử ghi rõ tên ca sĩ xem!'}), 404

        return jsonify({
            'title': song_input.upper(), # Lấy luôn cái người dùng nhập làm tiêu đề
            'lrc': lrc_content
        })

    except Exception as e:
        print(f"Lỗi: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/analyze-lyrics', methods=['POST'])
def analyze_lyrics():
    if not GEMINI_API_KEY:
        return jsonify({'error': 'Chưa cấu hình Gemini API Key'}), 500
        
    data = request.json
    lyrics_text = data.get('lyrics')
    
    if not lyrics_text: return jsonify({'error': 'No lyrics'}), 400

    try:
        prompt = f"""
        Analyze these lyrics. Return JSON ONLY (no markdown):
        Lyrics: {lyrics_text[:3000]}
        Format:
        {{
            "meaning": "Vietnamese summary (2 sentences)",
            "difficulty": "Easy/Medium/Hard",
            "vocabulary": [{{"word": "English", "mean": "Vietnamese"}}]
        }}
        """
        response = model.generate_content(prompt)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return clean_json

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)