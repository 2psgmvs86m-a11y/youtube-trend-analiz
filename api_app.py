from flask import Flask, jsonify, request, send_from_directory
from googleapiclient.discovery import build
from datetime import datetime
import os
import pandas as pd
import requests # HTML tarama için

app = Flask(__name__, static_folder='static')

API_KEY = os.environ.get("YOUTUBE_API_KEY")
if not API_KEY:
    print("HATA: API Anahtarı yok.")

youtube = build('youtube', 'v3', developerKey=API_KEY)

# --- ÖZEL: GERÇEK MONETİZASYON KONTROLÜ (SCRAPING) ---
def check_real_monetization(channel_id):
    url = f"https://www.youtube.com/channel/{channel_id}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        text = response.text
        if '"key":"is_monetization_enabled","value":"true"' in text: return True
        elif '"key":"is_monetization_enabled","value":"false"' in text: return False
        return None
    except: return None

# --- YARDIMCI FONKSİYONLAR ---
def resolve_channel_id(input_str):
    if input_str.startswith("UC") and len(input_str) == 24: return input_str
    try:
        search_response = youtube.search().list(q=input_str, type='channel', part='snippet', maxResults=1).execute()
        items = search_response.get('items', [])
        if items: return items[0]['snippet']['channelId']
    except: return None
    return None

def calculate_earnings(view_count):
    # Ortalama CPM $0.25 - $4.00
    min_earnings = (view_count / 1000) * 0.25
    max_earnings = (view_count / 1000) * 4.00
    return min_earnings, max_earnings

def get_channel_stats(channel_id):
    try:
        # 1. API Verileri
        request = youtube.channels().list(part="snippet,statistics,brandingSettings,contentDetails", id=channel_id)
        response = request.execute()
        items = response.get('items', [])
        if not items: return None
        
        item = items[0]
        snippet = item.get('snippet', {})
        stats = item.get('statistics', {})
        branding = item.get('brandingSettings', {})
        content_details = item.get('contentDetails', {})
        
        sub_count = int(stats.get('subscriberCount', 0))
        view_count = int(stats.get('viewCount', 0))
        video_count = int(stats.get('videoCount', 0))
        
        # 2. Gerçek Monetizasyon Kontrolü
        is_monetized_bool = check_real_monetization(channel_id)
        if is_monetized_bool is True:
            mon_status = "✅ AÇIK (Doğrulandı)"
            mon_color = "#28a745" # Yeşil
        elif is_monetized_bool is False:
            mon_status = "❌ KAPALI (Doğrulandı)"
            mon_color = "#dc3545" # Kırmızı
        else:
            # YEDEK PLAN (Tahmin)
            if sub_count >= 1000:
                mon_status = "⚠️ AÇIK Olabilir (Tahmin)"
                mon_color = "#ffc107" # Sarı
            else:
                mon_status = "❌ KAPALI (Abone Yetersiz)"
                mon_color = "#dc3545"

        # 3. Son Videolar
        uploads_id = content_details.get('relatedPlaylists', {}).get('uploads')
        recent_videos = []
        last_date = "Bilinmiyor"
        if uploads_id:
            try:
                pl_req = youtube.playlistItems().list(part="snippet", playlistId=uploads_id, maxResults=5)
                pl_res = pl_req.execute()
                for vid in pl_res.get('items', []):
                    vs = vid.get('snippet', {})
                    recent_videos.append({
                        "title": vs.get('title'),
                        "thumbnail": vs.get('thumbnails', {}).get('medium', {}).get('url'),
                        "publishedAt": vs.get('publishedAt')[0:10],
                        "videoId": vs.get('resourceId', {}).get('videoId')
                    })
                if recent_videos: last_date = recent_videos[0]['publishedAt']
            except: pass

        # Hesaplamalar
        avg = view_count / video_count if video_count > 0 else 0
        min_e, max_e = calculate_earnings(view_count)
        
        # Skor
        score = "C"
        if sub_count > 0:
            r = view_count / sub_count
            if r > 500: score = "A+"
            elif r > 200: score = "A"
            elif r > 100: score = "B"

        return {
            "title": snippet.get('title'),
            "description": snippet.get('description', ''),
            "customUrl": snippet.get('customUrl', ''),
            "country": snippet.get('country', 'TR'),
            "creation_date": snippet.get('publishedAt', '')[0:10],
            "last_upload_date": last_date,
            "subscribers": f"{sub_count:,}",
            "views": f"{view_count:,}",
            "video_count": f"{video_count:,}",
            "avg_views": f"{int(avg):,}",
            "est_earnings_min": f"${int(min_e):,}",
            "est_earnings_max": f"${int(max_e):,}",
            "score": score,
            "is_monetized": mon_status,
            "monetization_color": mon_color,
            "keywords": branding.get('channel', {}).get('keywords', ''),
            "banner_url": branding.get('image', {}).get('bannerExternalUrl', ''),
            "thumbnail": snippet.get('thumbnails', {}).get('high', {}).get('url'),
            "recent_videos": recent_videos
        }
    except: return None

def get_trending_videos(region_code="TR", max_results=5):
    try:
        request = youtube.videos().list(part="snippet,statistics", chart="mostPopular", regionCode=region_code, maxResults=max_results)
        response = request.execute()
        data = []
        for item in response.get("items", []):
            data.append({
                "title": item['snippet']['title'],
                "channel": item['snippet']['channelTitle'],
                "views": int(item['statistics'].get('viewCount', 0)),
                "url": f"https://www.youtube.com/watch?v={item['id']}",
                "thumbnail": item['snippet']['thumbnails']['medium']['url'],
                "tags": item['snippet'].get('tags', [])
            })
        return pd.DataFrame(data)
    except: return pd.DataFrame()

# --- ROTALAR ---
@app.route('/')
def home(): return send_from_directory(app.static_folder, 'index.html')
@app.route('/sorgula')
def query_page(): return send_from_directory(app.static_folder, 'channel_query.html')
@app.route('/analiz')
def analysis_page(): return send_from_directory(app.static_folder, 'trend_analysis.html')

@app.route('/api/trending', methods=['GET'])
def api_trending():
    region = request.args.get('region', 'TR')
    limit = int(request.args.get('limit', 5))
    df = get_trending_videos(region, limit)
    return jsonify(df.to_dict(orient='records'))

@app.route('/api/channel_stats', methods=['GET'])
def api_channel():
    q = request.args.get('query')
    if not q: return jsonify({"error": "Query required"}), 400
    
    clean = q
    if "/channel/" in q: clean = q.split("/channel/")[1].split("/")[0]
    elif "/@" in q: clean = q.split("/@")[1].split("/")[0]
    
    cid = resolve_channel_id(clean)
    if cid:
        stats = get_channel_stats(cid)
        if stats: return jsonify(stats)
    return jsonify({"error": "Kanal bulunamadı"}), 404

if __name__ == '__main__':
    app.run(debug=True)
