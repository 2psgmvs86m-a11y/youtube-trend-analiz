from flask import Flask, jsonify, request, send_from_directory
from googleapiclient.discovery import build
from datetime import datetime
import os
import pandas as pd

app = Flask(__name__, static_folder='static') 

# --- GUVENLIK: API Anahtarini Ortam Degiskenlerinden Cek ---
API_KEY = os.environ.get("YOUTUBE_API_KEY")

if not API_KEY:
    print("HATA: YouTube API anahtarı ayarlanmamış.")
    exit()

# API Servisini Baslatma
youtube = build('youtube', 'v3', developerKey=API_KEY)

# --- Veri Cekme Fonksiyonlari ---

def get_trending_videos(region_code="TR", max_results=30):
    """Belirtilen bolgedeki trend videoları çeker."""
    # (Mevcut kodunuz)
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

def get_channel_stats(channel_id):
    """Kanal ID'si ile tüm detaylı istatistikleri çeker."""
    request = youtube.channels().list(
        part="snippet,statistics,contentDetails,status",
        id=channel_id
    )
    response = request.execute()
    item = response.get('items', [{}])[0]
    
    if not item:
        return None
        
    snippet = item.get('snippet', {})
    stats = item.get('statistics', {})
    status = item.get('status', {})
    
    # Kanal Kayıt Tarihini Formatlama
    published_at_str = snippet.get('publishedAt')
    if published_at_str:
        published_date = datetime.strptime(published_at_str, '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%d %B %Y')
    else:
        published_date = "Bilinmiyor"

    # Para Kazanma Durumu (Monetizasyon) Tahmini
    # API doğrudan bilgi vermediği için YouTube Partner Programı (YPP) kriterlerini temel alıyoruz.
    monetization_status = "Bilinmiyor"
    sub_count = int(stats.get('subscriberCount', 0))
    # YPP kriterleri: 1000 abone ve 4000 saat izlenme (izlenme saati API'dan çekilemez, yaklaşık tahminde bulunuyoruz)
    if sub_count >= 1000:
        monetization_status = "Yüksek İhtimalle AÇIK (1K Abone Şartı Tamam)"
    else:
        monetization_status = "Kapalı (1K Abone Şartı Eksik)"

    # Verileri birleştirme
    data = {
        "title": snippet.get('title'),
        "subscribers": f"{int(stats.get('subscriberCount', 0)):,}",
        "views": f"{int(stats.get('viewCount', 0)):,}",
        "category": snippet.get('customUrl', 'Yok'),
        "creation_date": published_date,
        "is_monetized": monetization_status,
        "country": snippet.get('country', 'Belirtilmemiş'),
        "thumbnail": snippet.get('thumbnails', {}).get('high', {}).get('url')
    }
    return data

# --- API Uç Noktalari ---

@app.route('/')
def serve_index():
    """Kök URL'ye (/) gelen isteklere static/index.html dosyasını döndürür."""
    # Trend Analizi ana sayfa olacak
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/trending', methods=['GET'])
def trending_data():
    """HTML/JS'in cekecegi JSON verisini döndürür."""
    region = request.args.get('region', 'TR')
    df = get_trending_videos(region_code=region, max_results=30)
    return jsonify(df.to_dict(orient='records'))

# --- YENİ KANAL SORGULAMA ROTASI ---
@app.route('/api/channel_stats', methods=['GET'])
def channel_stats_data():
    """Kanal ID'sine göre detaylı istatistik döndürür."""
    channel_id = request.args.get('id')
    if not channel_id:
        return jsonify({"error": "Channel ID required"}), 400

    stats = get_channel_stats(channel_id)
    if stats:
        return jsonify(stats)
    else:
        return jsonify({"error": "Channel not found or API error"}), 404

if __name__ == '__main__':
    app.run(debug=True)
