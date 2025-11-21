from flask import Flask, jsonify, request, send_from_directory
from googleapiclient.discovery import build
from datetime import datetime
import os
import pandas as pd

app = Flask(__name__, static_folder='static')

API_KEY = os.environ.get("YOUTUBE_API_KEY")
if not API_KEY:
    print("HATA: API Anahtarı yok.")
    exit()

youtube = build('youtube', 'v3', developerKey=API_KEY)

# --- YARDIMCI FONKSİYONLAR ---

def resolve_channel_id(input_str):
    """Girdiyi (Link, Handle, İsim) Kanal ID'sine çevirir."""
    # 1. Eğer zaten ID formatındaysa (UC ile başlar ve 24 karakterdir)
    if input_str.startswith("UC") and len(input_str) == 24:
        return input_str

    # 2. Değilse, YouTube Search API ile arama yap
    try:
        search_response = youtube.search().list(
            q=input_str,
            type='channel',
            part='snippet',
            maxResults=1
        ).execute()
        
        items = search_response.get('items', [])
        if items:
            return items[0]['snippet']['channelId']
    except:
        return None
    return None

def get_trending_videos(region_code="TR", max_results=10):
    """Trendleri çeker."""
    request = youtube.videos().list(
        part="snippet,statistics",
        chart="mostPopular",
        regionCode=region_code,
        maxResults=max_results
    )
    response = request.execute()
    
    video_data = []
    for item in response.get("items", []):
        # Etiketleri (Tags) alalım - Rekabet analizi için
        tags = item['snippet'].get('tags', [])
        
        video_data.append({
            "title": item['snippet']['title'],
            "channel": item['snippet']['channelTitle'],
            "views": int(item['statistics'].get('viewCount', 0)),
            "likes": int(item['statistics'].get('likeCount', 0)),
            "url": f"https://www.youtube.com/watch?v={item['id']}",
            "thumbnail": item['snippet']['thumbnails']['medium']['url'],
            "tags": tags
        })
    return pd.DataFrame(video_data)

def get_channel_stats(channel_id):
    """Kanal detaylarını çeker."""
    request = youtube.channels().list(
        part="snippet,statistics,brandingSettings,topicDetails",
        id=channel_id
    )
    response = request.execute()
    items = response.get('items', [])
    
    if not items:
        return None
        
    item = items[0]
    snippet = item.get('snippet', {})
    stats = item.get('statistics', {})
    branding = item.get('brandingSettings', {})
    
    # Veri Hazırlığı
    published_at = snippet.get('publishedAt', '')
    if published_at:
        published_date = datetime.strptime(published_at, '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%d %B %Y')
    else:
        published_date = "Bilinmiyor"

    sub_count = int(stats.get('subscriberCount', 0))
    monetization = "✅ AÇIK Olabilir" if sub_count >= 1000 else "❌ KAPALI (Abone Yetersiz)"

    return {
        "title": snippet.get('title'),
        "description": snippet.get('description', ''),
        "customUrl": snippet.get('customUrl', ''),
        "country": snippet.get('country', 'TR'),
        "creation_date": published_date,
        "subscribers": f"{sub_count:,}",
        "views": f"{int(stats.get('viewCount', 0)):,}",
        "video_count": f"{int(stats.get('videoCount', 0)):,}",
        "is_monetized": monetization,
        "keywords": branding.get('channel', {}).get('keywords', ''),
        "banner_url": branding.get('image', {}).get('bannerExternalUrl', ''),
        "thumbnail": snippet.get('thumbnails', {}).get('high', {}).get('url')
    }

# --- ROTALAR ---

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/trending', methods=['GET'])
def trending_data():
    region = request.args.get('region', 'TR')
    # Frontend'den limit isteği gelirse onu kullan, yoksa 30 getir
    limit = int(request.args.get('limit', 30)) 
    
    df = get_trending_videos(region_code=region, max_results=limit)
    return jsonify(df.to_dict(orient='records'))

@app.route('/api/channel_stats', methods=['GET'])
def channel_stats_data():
    # Kullanıcı link, handle (@) veya isim girebilir
    query = request.args.get('query')
    
    if not query:
        return jsonify({"error": "Query required"}), 400
    
    # Linkten ID çıkarma (Basit temizlik)
    clean_query = query
    if "youtube.com" in query or "youtu.be" in query:
        if "/channel/" in query:
            clean_query = query.split("/channel/")[1].split("/")[0]
        elif "/@" in query:
            clean_query = query.split("/@")[1].split("/")[0] # Handle'ı al
        # Link temizlendiyse veya direkt isim geldiyse resolve et
    
    # ID'yi bul (API ile)
    channel_id = resolve_channel_id(clean_query)
    
    if channel_id:
        stats = get_channel_stats(channel_id)
        if stats:
            return jsonify(stats)
    
    return jsonify({"error": "Kanal bulunamadı. Lütfen ismini doğru yazdığınızdan emin olun."}), 404

if __name__ == '__main__':
    app.run(debug=True)
