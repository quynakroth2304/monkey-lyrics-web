from flask import Flask, render_template, request, jsonify
import yt_dlp
import syncedlyrics
import google.generativeai as genai
import re

app = Flask(__name__)

# --- CẤU HÌNH API GEMINI ---
GEMINI_API_KEY = "AIzaSyCVSjO8txkpPYSC7IiPAjdi9kHzDM-CooA"
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
        return jsonify({'error': 'Nhập tên bài hoặc link đi bạn!'}), 400

    try:
        print(f"--- Đang tìm lời cho: {song_input} ---")
        
        # Cấu hình yt-dlp: KHÔNG TẢI AUDIO nưa, chỉ lấy thông tin
        ydl_opts = {
            'noplaylist': True,
            'quiet': True,
            'skip_download': True, # <--- QUAN TRỌNG: Tắt tải nhạc
        }

        if song_input.startswith(('http://', 'https://')):
            search_query = song_input
        else:
            search_query = f"ytsearch1:{song_input}"

        title = ""
        clean_title = ""

        # 1. Lấy tên bài hát từ Youtube (Siêu nhanh)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False) # Download = False
            video_info = info['entries'][0] if 'entries' in info else info
            title = video_info['title']
            
            # Làm sạch tên để tìm lời cho dễ
            clean_title = re.sub(r"[\(\[].*?[\)\]]", "", title).strip()
            clean_title = clean_title.split('|')[0].strip()

        # 2. Tìm lời bài hát
        print(f"Đang tìm LRC cho: {clean_title}")
        lrc_content = syncedlyrics.search(clean_title)
        
        if not lrc_content:
            # Thử tìm bằng tên gốc nếu tên sạch không ra
            lrc_content = syncedlyrics.search(title)
            
        if not lrc_content:
            return jsonify({'error': 'Không tìm thấy lời bài này. Thử bài khác xem!'}), 404

        return jsonify({
            'title': title,
            'lrc': lrc_content
        })

    except Exception as e:
        print(f"Lỗi: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/analyze-lyrics', methods=['POST'])
def analyze_lyrics():
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