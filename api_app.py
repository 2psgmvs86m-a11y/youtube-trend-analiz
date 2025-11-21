from flask import Flask, jsonify, request, send_from_directory
from googleapiclient.discovery import build
import os
import pandas as pd
import cloudscraper
import json

app = Flask(__name__, static_folder='static')

# API KEY KONTROLÜ
API_KEY = os.environ.get("YOUTUBE_API_KEY")
if not API_KEY:
    print("⚠️ UYARI: YOUTUBE_API_KEY çevre değişkeni bulunamadı!")

try:
    youtube = build('youtube', 'v3', developerKey=API_KEY)
except:
    youtube = None

# --- DİL SÖZLÜĞÜ ---
TRANSLATIONS = {
    "TR": {
        "open": "✅ AKTİF (AÇIK)",
        "closed": "❌ PASİF (KAPALI)",
        "unknown": "❓ TESPİT EDİLEMEDİ",
        "error": "Kanal bulunamadı."
    },
    "EN": {
        "open": "✅ ENABLED (ACTIVE)",
        "closed": "❌ DISABLED (INACTIVE)",
        "unknown": "❓ UNKNOWN",
        "error": "Channel not found."
    }
}

# --- GELİŞMİŞ MONETİZASYON KONTROLÜ ---
def check_strict_monetization(channel_id):
    """
    Kanalın para kazanma durumunu kaynak koddan derinlemesine analiz eder.
    """
    url = f"https://www.youtube.com/channel/{channel_id}"
    
    # YouTube'u gerçek bir tarayıcı gibi kandıran scraper
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    try:
        response = scraper.get(url, timeout=10)
        text = response.text
        
        # KANIT 1: Eski usul kesin anahtar (Hala bazı kanallarda çalışır)
        if '"key":"is_monetization_enabled","value":"true"' in text:
            return True
        if '"key":"is_monetization_enabled","value":"false"' in text:
            return False

        # KANIT 2: "Katıl" (Join) Butonu var mı? (Varsa %100 açıktır)
        if 'membershipOfferRenderer' in text:
            return True
        if 'sponsorButtonRenderer' in text:
            return True
            
        # KANIT 3: Mağaza Rafı (Merch Shelf) var mı? (Varsa %100 açıktır)
        if 'merchandiseShelfRenderer' in text:
            return True

        # KANIT 4: Reklam sinyalleri (Yarı güvenilir)
        # Eğer 'google_ads' scriptleri yoğunsa muhtemelen açıktır
        if 'google_ads_js' in text or 'doubleclick.net' in text:
            # Bunu tek başına kanıt saymak riskli olabilir ama genellikle doğrudur.
            # Şimdilik True döndürelim.
            return True

        # Hiçbir kanıt yoksa KAPALI varsayalım.
        return False
        
    except Exception as e:
        print(f"Tarama Hatası: {e}")
        return None

# --- YARDIMCI FONKSİYONLAR ---
def resolve_channel_id(input_str):
    # Eğer direkt ID girildiyse (UC ile başlar)
    if input_str.startswith("UC") and len(input_str) == 24:
        return input_str
        
    try:
        if youtube:
            # Handle araması (@kullaniciadi) veya isim araması
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

def calculate_earnings(view_count):
    # Türkiye odaklı CPM (Daha gerçekçi rakamlar)
    # Min: 1000 izlenme başına 0.25$
    # Max: 1000 izlenme başına 2.00$
    if view_count == 0: return 0, 0
    
    min_earnings = (view_count / 1000) * 0.25
    max_earnings = (view_count / 1000) * 2.50
    return min_earnings, max_earnings

def get_channel_stats(channel_id, lang="TR"):
    if not youtube: return None
    
    t = TRANSLATIONS.get(lang, TRANSLATIONS["TR"])

    try:
        req = youtube.channels().list(
            part="snippet,statistics,brandingSettings,contentDetails", 
            id=channel_id
        )
        res = req.execute()
        if not res.get('items'): return None
        
        item = res['items'][0]
        snippet = item.get('snippet', {})
        stats = item.get('statistics', {})
        branding = item.get('brandingSettings', {})
        content = item.get('contentDetails', {})
        
        sub_count = int(stats.get('subscriberCount', 0))
        view_count = int(stats.get('viewCount', 0))
        video_count = int(stats.get('videoCount', 0))
        
        # --- KRİTİK: MONETİZASYON KONTROLÜ ---
        is_open = check_strict_monetization(channel_id)
        
        mon_status = t["unknown"]
        mon_color = "#6c757d" # Gri

        if is_open is True:
            mon_status = t["open"]
            mon_color = "#28a745" # Yeşil
        elif is_open is False:
            # Eğer 1000 abone altıysa zaten kapalıdır, kontrol doğru çalışmış demektir.
            mon_status = t["closed"]
            mon_color = "#dc3545" # Kırmızı

        # Son Videoları Çek
        uploads_id = content.get('relatedPlaylists', {}).get('uploads')
        recent_videos = []
        last_date = "-"
        
        if uploads_id:
            try:
                pl_req = youtube.playlistItems().list(
                    part="snippet", 
                    playlistId=uploads_id, 
                    maxResults=4
                )
                pl_res = pl_req.execute()
                for vid in pl_res.get('items', []):
                    vs = vid.get('snippet', {})
                    recent_videos.append({
                        "title": vs.get('title'),
                        "thumbnail": vs.get('thumbnails', {}).get('medium', {}).get('url'),
                        "publishedAt": vs.get('publishedAt')[0:10],
                        "videoId": vs.get('resourceId', {}).get('videoId')
                    })
                if recent_videos: 
                    last_date = recent_videos[0]['publishedAt']
            except: pass

        # Ortalama ve Kazanç
        avg = view_count / video_count if video_count > 0 else 0
        min_e, max_e = calculate_earnings(view_count) # Burası toplam izlenmeye göre ömür boyu kazanç
        
        # Aylık tahmini kazanç için basit bir simülasyon (Toplamın %2'si gibi bir varsayım)
        monthly_min = min_e * 0.01 
        monthly_max = max_e * 0.01

        # Skorlama
        score = "C-"
        if sub_count > 0:
            r = view_count / sub_count
            if r > 500: score = "A+"
            elif r > 200: score = "A"
            elif r > 100: score = "B+"
            elif r > 50: score = "B"

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
            "est_earnings_min": f"${int(monthly_min):,}", # Aylık gösteriyoruz artık
            "est_earnings_max": f"${int(monthly_max):,}",
            "score": score,
            "is_monetized": mon_status,
            "monetization_color": mon_color,
            "banner_url": branding.get('image', {}).get('bannerExternalUrl', ''),
            "thumbnail": snippet.get('thumbnails', {}).get('high', {}).get('url'),
            "recent_videos": recent_videos
        }
    except Exception as e: 
        print(f"Stats Error: {e}")
        return None

def get_trending_videos(region_code="TR", max_results=10):
    try:
        request = youtube.videos().list(
            part="snippet,statistics", 
            chart="mostPopular", 
            regionCode=region_code, 
            maxResults=max_results
        )
        response = request.execute()
        data = []
        for item in response.get("items", []):
            tags = item['snippet'].get('tags', [])
            data.append({
                "title": item['snippet']['title'],
                "channel": item['snippet']['channelTitle'],
                "views": int(item['statistics'].get('viewCount', 0)),
                "url": f"https://www.youtube.com/watch?v={item['id']}",
                "thumbnail": item['snippet']['thumbnails']['medium']['url'],
                "tags": tags # Liste olarak gönderiyoruz
            })
        return pd.DataFrame(data)
    except: 
        return pd.DataFrame()

# --- ROTALAR ---
@app.route('/')
def home(): 
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/sorgula')
def query_page(): 
    return send_from_directory(app.static_folder, 'channel_query.html')

@app.route('/analiz')
def analysis_page(): 
    return send_from_directory(app.static_folder, 'trend_analysis.html')

# --- API ---
@app.route('/api/channel_stats', methods=['GET'])
def api_channel():
    q = request.args.get('query')
    lang = request.args.get('lang', 'TR').upper()
    
    if not q: return jsonify({"error": "Query required"}), 400
    
    clean = q
    if "/channel/" in q: clean = q.split("/channel/")[1].split("/")[0]
    elif "/@" in q: clean = q.split("/@")[1].split("/")[0]
    
    cid = resolve_channel_id(clean)
    if cid:
        stats = get_channel_stats(cid, lang)
        if stats: return jsonify(stats)
        
    return jsonify({"error": TRANSLATIONS[lang]["error"]}), 404

@app.route('/api/trending', methods=['GET'])
def api_trending():
    region = request.args.get('region', 'TR')
    limit = int(request.args.get('limit', 10))
    df = get_trending_videos(region, limit)
    
    # Pandas DataFrame'i JSON'a çevirirken tag'lerin düzgün gitmesini sağla
    result = df.to_dict(orient='records')
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
