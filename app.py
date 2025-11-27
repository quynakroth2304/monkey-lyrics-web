from flask import Flask, render_template, request, jsonify
import syncedlyrics
import os
import yt_dlp
import re

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

# --- 1. TÌM DANH SÁCH BÀI HÁT (Khi nhập tên) ---
@app.route('/search-list', methods=['POST'])
def search_list():
    query = request.json.get('query')
    if not query: return jsonify({'error': 'Nhập tên bài đi!'}), 400
    
    try:
        # Cấu hình yt-dlp chế độ "Ẩn mình" (Stealth mode)
        ydl_opts = {
            'quiet': True,
            'extract_flat': True, # CHỈ LẤY TEXT, KHÔNG CHẠM VÀO VIDEO
            'noplaylist': True,
            'limit': 5,
            'ignoreerrors': True # Bỏ qua lỗi nếu 1 video bị chặn
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch5:{query}", download=False)
            entries = info.get('entries', [])
            
            results = []
            for item in entries:
                if item: # Kiểm tra item tồn tại
                    results.append({'title': item['title'], 'id': item['id']})
            
            if not results:
                return jsonify({'error': 'Không tìm thấy. Hãy thử tên khác!'}), 404
                
            return jsonify(results)
    except Exception as e:
        print(f"Search Error: {e}")
        return jsonify({'error': 'Lỗi kết nối YouTube. Hãy thử lại!'}), 500

# --- 2. LẤY LỜI BÀI HÁT (Xử lý thông minh) ---
@app.route('/get-lyrics', methods=['POST'])
def get_lyrics():
    data = request.json
    title_or_link = data.get('title')
    
    clean_title = title_or_link

    # A. NẾU LÀ LINK: Cố gắng lấy tên bài hát
    if title_or_link.startswith(('http://', 'https://')):
        try:
            ydl_opts = {'quiet': True, 'skip_download': True, 'noplaylist': True, 'ignoreerrors': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(title_or_link, download=False)
                if not info:
                    return jsonify({'error': 'YouTube chặn link này rồi. Hãy NHẬP TÊN bài hát nhé!'}), 403
                clean_title = info.get('title', 'Unknown Song')
        except Exception:
            return jsonify({'error': 'Lỗi đọc Link. Hãy nhập Tên Bài Hát cho nhanh!'}), 400

    # B. LÀM SẠCH TÊN (Bỏ rác để tìm lời dễ hơn)
    # Ví dụ: "Son Tung M-TP - Lac Troi (Official MV)" -> "Lac Troi"
    try:
        # Bỏ phần trong ngoặc (...) và [...]
        clean_title = re.sub(r"[\(\[].*?[\)\]]", "", clean_title)
        # Bỏ phần sau dấu | hoặc - (thường là tên ca sĩ hoặc Official)
        if '|' in clean_title: clean_title = clean_title.split('|')[0]
        
        clean_title = clean_title.strip()
        print(f"Finding lyrics for: {clean_title}")

        # C. TÌM LỜI (Syncedlyrics)
        lrc = syncedlyrics.search(clean_title)
        
        # Fallback: Nếu tên sạch ko ra, tìm bằng tên gốc
        if not lrc: lrc = syncedlyrics.search(title_or_link)

        if not lrc:
            return jsonify({'error': f'Không tìm thấy lời cho bài: {clean_title}'}), 404

        return jsonify({'title': clean_title, 'lrc': lrc})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)