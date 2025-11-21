from flask import Flask, jsonify, request, send_from_directory
from googleapiclient.discovery import build
from datetime import datetime
import os
import pandas as pd

# Static klasörünü tanımlıyoruz
app = Flask(__name__, static_folder='static')

API_KEY = os.environ.get("YOUTUBE_API_KEY")
if not API_KEY:
    print("HATA: API Anahtarı yok.")

youtube = build('youtube', 'v3', developerKey=API_KEY)

# --- YARDIMCI FONKSİYONLAR ---
def resolve_channel_id(input_str):
    if input_str.startswith("UC") and len(input_str) == 24:
        return input_str
    try:
        search_response = youtube.search().list(q=input_str, type='channel', part='snippet', maxResults=1).execute()
        items = search_response.get('items', [])
        if items: return items[0]['snippet']['channelId']
    except: return None
    return None

def get_channel_stats(channel_id):
    try:
        request = youtube.channels().list(part="snippet,statistics,brandingSettings,topicDetails", id=channel_id)
        response = request.execute()
        items = response.get('items', [])
        if not items: return None
        
        item = items[0]
        snippet = item.get('snippet', {})
        stats = item.get('statistics', {})
        branding = item.get('brandingSettings', {})
        
        sub_count = int(stats.get('subscriberCount', 0))
        keywords = branding.get('channel', {}).get('keywords', '')

        return {
            "title": snippet.get('title'),
            "description": snippet.get('description', ''),
            "customUrl": snippet.get('customUrl', ''),
            "country": snippet.get('country', 'TR'),
            "creation_date": snippet.get('publishedAt', '')[0:10],
            "subscribers": f"{sub_count:,}",
            "views": f"{int(stats.get('viewCount', 0)):,}",
            "video_count": f"{int(stats.get('videoCount', 0)):,}",
            "is_monetized": "✅ AÇIK Olabilir" if sub_count >= 1000 else "❌ KAPALI",
            "keywords": keywords,
            "banner_url": branding.get('image', {}).get('bannerExternalUrl', ''),
            "thumbnail": snippet.get('thumbnails', {}).get('high', {}).get('url')
        }
    except: return None

def get_trending_videos(region_code="TR", max_results=5):
    try:
        request = youtube.videos().list(part="snippet,statistics", chart="mostPopular", regionCode=region_code, maxResults=max_results)
        response = request.execute()
        video_data = []
        for item in response.get("items", []):
            video_data.append({
                "title": item['snippet']['title'],
                "channel": item['snippet']['channelTitle'],
                "views": int(item['statistics'].get('viewCount', 0)),
                "url": f"https://www.youtube.com/watch?v={item['id']}",
                "thumbnail": item['snippet']['thumbnails']['medium']['url']
            })
        return pd.DataFrame(video_data)
    except: return pd.DataFrame()

# --- KRİTİK KISIM: ROTALAR (ROUTES) ---
# Bu kısım eksik olduğu için 404 hatası alıyordun.

@app.route('/')
def home():
    # Ana sayfa
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/sorgula')
def query_page():
    # Kanal sorgulama sayfası rotası
    return send_from_directory(app.static_folder, 'channel_query.html')

@app.route('/analiz')
def analysis_page():
    # Detaylı analiz sayfası rotası
    return send_from_directory(app.static_folder, 'trend_analysis.html')

# API Veri Rotaları
@app.route('/api/trending', methods=['GET'])
def api_trending():
    region = request.args.get('region', 'TR')
    limit = int(request.args.get('limit', 5))
    df = get_trending_videos(region, limit)
    return jsonify(df.to_dict(orient='records'))

@app.route('/api/channel_stats', methods=['GET'])
def api_channel():
    query = request.args.get('query')
    if not query: return jsonify({"error": "Query required"}), 400
    
    # Temizlik
    clean_query = query
    if "/channel/" in query: clean_query = query.split("/channel/")[1].split("/")[0]
    elif "/@" in query: clean_query = query.split("/@")[1].split("/")[0]
    
    cid = resolve_channel_id(clean_query)
    if cid:
        stats = get_channel_stats(cid)
        if stats: return jsonify(stats)
    return jsonify({"error": "Kanal bulunamadı"}), 404

if __name__ == '__main__':
    app.run(debug=True)
