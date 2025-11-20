from flask import Flask, jsonify, request
from googleapiclient.discovery import build
import os
import pandas as pd

app = Flask(__name__)

# --- GUVENLIK: API Anahtarini Ortam Degiskenlerinden Cek ---
API_KEY = os.environ.get("YOUTUBE_API_KEY")

if not API_KEY:
    # Gerçek uygulamada bu hata loglanmalıdır, ancak burada kullanıcıya bildiriyoruz
    print("HATA: YouTube API anahtarı ayarlanmamış.")
    exit()

# API Servisini Baslatma
youtube = build('youtube', 'v3', developerKey=API_KEY)

# --- Veri Cekme Fonksiyonu ---
def get_trending_videos(region_code="TR", max_results=30):
    """Belirtilen bolgedeki trend videoları çeker ve DataFrame döndürür."""
    request = youtube.videos().list(
        part="snippet,statistics",
        chart="mostPopular",
        regionCode=region_code,
        maxResults=max_results
    )
    response = request.execute()
    
    video_data = []
    for item in response.get("items", []):
        video_data.append({
            "title": item['snippet']['title'],
            "channel": item['snippet']['channelTitle'],
            "views": int(item['statistics'].get('viewCount', 0)),
            "url": f"https://www.youtube.com/watch?v={item['id']}"
        })
    return pd.DataFrame(video_data)

# --- API Uç Noktası (Endpoint) ---
@app.route('/api/trending', methods=['GET'])
def trending_data():
    """HTML/JS'in cekecegi JSON verisini döndürür."""
    region = request.args.get('region', 'TR') # URL'den bolge parametresini alir
    
    df = get_trending_videos(region_code=region, max_results=30)
    
    # Pandas DataFrame'i JSON'a cevirip döndürüyoruz
    return jsonify(df.to_dict(orient='records'))

if __name__ == '__main__':
    # Render, api_app yerine gunicorn kullanacaktir
    app.run(debug=True)

