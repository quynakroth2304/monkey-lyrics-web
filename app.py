from flask import Flask, render_template, request, jsonify
import syncedlyrics
import os
import yt_dlp
import re

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

# --- API XỬ LÝ TỰ ĐỘNG (AUTO PICK) ---
@app.route('/get-song-auto', methods=['POST'])
def get_song_auto():
    query = request.json.get('query')
    if not query: return jsonify({'error': 'Nhập tên bài đi!'}), 400
    
    try:
        real_title = query
        
        # 1. LẤY TÊN CHUẨN (TỪ LINK HOẶC TỪ KHÓA)
        # Cấu hình yt-dlp lấy thông tin nhanh nhất (không tải video)
        ydl_opts = {
            'quiet': True,
            'extract_flat': True, 
            'noplaylist': True,
            'limit': 1 # CHỈ LẤY ĐÚNG 1 KẾT QUẢ TỐT NHẤT
        }
        
        search_query = query
        if not query.startswith(('http://', 'https://')):
            search_query = f"ytsearch1:{query}" # Tìm kiếm trên Youtube nếu không phải link

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            
            if 'entries' in info:
                # Nếu là tìm kiếm, lấy video đầu tiên
                if len(info['entries']) > 0:
                    real_title = info['entries'][0]['title']
                else:
                    return jsonify({'error': 'Không tìm thấy bài nào!'}), 404
            else:
                # Nếu là link trực tiếp
                real_title = info.get('title', query)

        # 2. LÀM SẠCH TÊN ĐỂ TÌM LỜI
        # Ví dụ: "Son Tung M-TP - Lac Troi (Official MV)" -> "Lac Troi"
        clean_title = re.sub(r"[\(\[].*?[\)\]]", "", real_title) 
        clean_title = clean_title.split('|')[0].strip()
        if '-' in clean_title:
            parts = clean_title.split('-')
            if len(parts) >= 2: clean_title = parts[1].strip()

        print(f"Original: {real_title} -> Search Lyrics: {clean_title}")

        # 3. TÌM LỜI
        lrc = syncedlyrics.search(clean_title)
        
        # Fallback: Tìm bằng tên gốc nếu tên sạch ko ra
        if not lrc: lrc = syncedlyrics.search(real_title)
        
        if not lrc: 
            return jsonify({'error': f'Không tìm thấy lời cho bài: {clean_title}'}), 404
            
        return jsonify({'title': real_title, 'lrc': lrc})

    except Exception as e:
        print(e)
        return jsonify({'error': 'Lỗi xử lý. Thử lại tên khác xem!'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)