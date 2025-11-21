import os
import requests
import json
from flask import Flask, render_template, request
from datetime import datetime
from collections import Counter

app = Flask(__name__)

# API Anahtarı
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')

translations = {
    'tr': {
        'title': 'YouTube Kanal Denetçisi',
        'search_btn': 'KANALI DENETLE',
        'placeholder': 'Kanal Adı veya Linki...',
        'grade': 'Kanal Notu',
        'upload_schedule': 'Yükleme Sıklığı',
        'tags': 'Kanal Etiketleri',
        'category': 'Kategori',
        'monetization': 'Para Kazanma',
        'earnings': 'Tahmini Aylık Gelir',
        'active': 'AÇIK / AKTİF ✅',
        'passive': 'KAPALI / RİSKLİ ❌',
        'subs': 'Abone',
        'views': 'Görüntülenme',
        'videos': 'Video',
        'engagement': 'Etkileşim Oranı',
        'error': 'Kanal bulunamadı!',
        'latest': 'Son Yüklemeler',
        'warn_monetization': 'Kanalın para kazanma durumu doğrulanamadı veya kapalı.'
    },
    'en': {
        'title': 'YouTube Channel Auditor',
        'search_btn': 'AUDIT CHANNEL',
        'placeholder': 'Channel Name or Link...',
        'grade': 'Channel Grade',
        'upload_schedule': 'Upload Schedule',
        'tags': 'Channel Tags',
        'category': 'Niche / Category',
        'monetization': 'Monetization',
        'earnings': 'Est. Monthly Revenue',
        'active': 'ENABLED ✅',
        'passive': 'DISABLED ❌',
        'subs': 'Subscribers',
        'views': 'Views',
        'videos': 'Videos',
        'engagement': 'Engagement Rate',
        'error': 'Channel not found!',
        'latest': 'Latest Uploads',
        'warn_monetization': 'Monetization status could not be verified or is disabled.'
    },
    'de': {
        'title': 'YouTube-Kanal-Auditor',
        'search_btn': 'KANAL PRÜFEN',
        'placeholder': 'Kanalname oder Link...',
        'grade': 'Kanalnote',
        'upload_schedule': 'Upload-Zeitplan',
        'tags': 'Kanal-Tags',
        'category': 'Kategorie',
        'monetization': 'Monetarisierung',
        'earnings': 'Geschätzter Umsatz',
        'active': 'AKTIV ✅',
        'passive': 'INAKTIV ❌',
        'subs': 'Abonnenten',
        'views': 'Aufrufe',
        'videos': 'Videos',
        'engagement': 'Engagement-Rate',
        'error': 'Kanal nicht gefunden!',
        'latest': 'Neueste Uploads',
        'warn_monetization': 'Monetarisierungsstatus konnte nicht überprüft werden.'
    }
}

def format_number(num):
    if num > 1000000: return f"{num/1000000:.1f}M"
    if num > 1000: return f"{num/1000:.1f}K"
    return str(num)

# --- YENİ PUANLAMA SİSTEMİ (DAHA ZOR VE GERÇEKÇİ) ---
def calculate_grade(sub_count, view_count, video_count):
    if sub_count == 0 or video_count == 0: return "D"
    
    # 1. Etkileşim Oranı (Ortalama İzlenme / Abone Sayısı)
    avg_views = view_count / video_count
    engagement_rate = (avg_views / sub_count) * 100 if sub_count > 0 else 0
    
    score = 0
    
    # A) OTORİTE PUANI (Max 30 Puan) - Büyük kanallar daha yüksek not alır
    if sub_count >= 1000000: score += 30
    elif sub_count >= 500000: score += 25
    elif sub_count >= 100000: score += 20
    elif sub_count >= 10000: score += 10
    elif sub_count >= 1000: score += 5
    
    # B) ETKİLEŞİM PUANI (Max 50 Puan) - İzleyicisini tutan kazanır
    if engagement_rate >= 20: score += 50      # Viral / Çok sadık kitle
    elif engagement_rate >= 10: score += 40    # Mükemmel
    elif engagement_rate >= 5: score += 30     # İyi
    elif engagement_rate >= 2: score += 20     # Ortalama
    elif engagement_rate >= 1: score += 10     # Düşük
    else: score += 5
    
    # C) İSTİKRAR PUANI (Max 20 Puan) - Video sayısı
    if video_count >= 1000: score += 20
    elif video_count >= 300: score += 15
    elif video_count >= 50: score += 10
    else: score += 5

    # --- DÜZELTME ---
    # 1000 abonenin altındaki kanallar, ne kadar iyi olursa olsun Max 'B' alabilir.
    if sub_count < 1000 and score > 60:
        score = 60

    # Harf Notuna Çevirme
    if score >= 90: return "A+"
    if score >= 80: return "A"
    if score >= 65: return "B+"
    if score >= 50: return "B"
    if score >= 35: return "C"
    return "D"
# -----------------------------------------------------

# --- GARANTİCİ MONETIZATION KONTROLÜ ---
def check_real_monetization(channel_id):
    try:
        url = f"https://www.youtube.com/channel/{channel_id}"
        
        # Render için Bot Duvarını Aşma (Cookie Injection)
        cookies = {
            'CONSENT': 'YES+cb.20220301-11-p0.en+FX+419',
            'SOCS': 'CAISNQgDEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjMwMTI0LjA2X3AxGgJlbiACGgYIgJ-NowY'
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/"
        }
        
        response = requests.get(url, headers=headers, cookies=cookies, timeout=5)
        text = response.text
        
        if '"key":"is_monetization_enabled","value":"true"' in text: return True
        if 'sponsorButtonRenderer' in text: return True
        if 'merchandiseShelfRenderer' in text: return True
        if 'is_monetization_enabled' in text and 'true' in text: return True

        return False
    except Exception as e:
        print(f"Scraping hatası: {e}")
        return False 
# -----------------------------------------

def get_niche_cpm(tags_list, title, desc):
    full_text = " ".join(tags_list).lower() + " " + title.lower() + " " + desc.lower()
    
    finance_keys = ['finance', 'crypto', 'bitcoin', 'money', 'business', 'finans', 'para', 'borsa', 'passive income']
    tech_keys = ['tech', 'review', 'phone', 'apple', 'teknoloji', 'inceleme', 'yazılım', 'coding', 'pc']
    game_keys = ['game', 'gaming', 'play', 'minecraft', 'roblox', 'oyun', 'pubg', 'valorant']
    vlog_keys = ['vlog', 'life', 'daily', 'eğlence', 'challenge', 'prank']
    news_keys = ['news', 'haber', 'siyaset', 'politics']

    if any(word in full_text for word in finance_keys):
        return 8.00, "Finans / Ekonomi 💰"
    elif any(word in full_text for word in tech_keys):
        return 4.50, "Teknoloji / Eğitim 💻"
    elif any(word in full_text for word in game_keys):
        return 1.20, "Gaming / Oyun 🎮"
    elif any(word in full_text for word in vlog_keys):
        return 2.00, "Eğlence / Vlog 🎬"
    elif any(word in full_text for word in news_keys):
        return 1.50, "Haber / Gündem 📰"
    
    return 2.00, "Genel / Karma 🌍"

def get_channel_data(query, lang_code='tr'):
    if not YOUTUBE_API_KEY: raise Exception("API Key Yok!")

    search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=channel&key={YOUTUBE_API_KEY}"
    search_res = requests.get(search_url).json()
    if not search_res.get('items'): return None
    channel_id = search_res['items'][0]['id']['channelId']

    stats_url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics,snippet,contentDetails,brandingSettings&id={channel_id}&key={YOUTUBE_API_KEY}"
    stats_res = requests.get(stats_url).json()
    info = stats_res['items'][0]
    stats = info['statistics']
    snippet = info['snippet']

    sub_count = int(stats.get('subscriberCount', 0))
    view_count = int(stats.get('viewCount', 0))
    video_count = int(stats.get('videoCount', 0))
    
    keywords = []
    if 'brandingSettings' in info and 'channel' in info['brandingSettings']:
        keys = info['brandingSettings']['channel'].get('keywords', '')
        if keys:
            keywords = [k.replace('"', '') for k in keys.split(' ')[:10]]

    uploads_id = info['contentDetails']['relatedPlaylists']['uploads']
    videos_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={uploads_id}&maxResults=10&key={YOUTUBE_API_KEY}"
    videos_res = requests.get(videos_url).json()

    videos = []
    upload_hours = []
    
    for item in videos_res.get('items', []):
        pub_time = item['snippet']['publishedAt']
        dt = datetime.strptime(pub_time, "%Y-%m-%dT%H:%M:%SZ")
        upload_hours.append(dt.hour)
        
        if len(videos) < 3:
            videos.append({
                'title': item['snippet']['title'],
                'thumb': item['snippet']['thumbnails']['high']['url'],
                'id': item['snippet']['resourceId']['videoId'],
                'published': dt.strftime("%d.%m.%Y")
            })

    peak_hour_str = "Belirsiz"
    if upload_hours:
        common_hour = Counter(upload_hours).most_common(1)[0][0]
        tr_hour = (common_hour + 3) % 24
        peak_hour_str = f"{tr_hour}:00 - {tr_hour+1}:00 (TR)"

    cpm, niche_name = get_niche_cpm(keywords, snippet['title'], snippet['description'])
    est_monthly_views = view_count * 0.03 
    monthly_rev = (est_monthly_views / 1000) * cpm
    
    # --- GARANTİCİ MONETIZATION MANTIĞI ---
    is_monetized = False
    if sub_count >= 1000:
        scraping_result = check_real_monetization(channel_id)
        if scraping_result:
            is_monetized = True
        else:
            # Scraping başarısızsa büyük kanalları yakma (Safety Net)
            if sub_count > 5000 and view_count > 100000:
                is_monetized = True
            else:
                is_monetized = False
    
    earnings_str = f"${monthly_rev * 0.8:,.0f} - ${monthly_rev * 1.2:,.0f}" if is_monetized else "$0"
    status_key = 'active' if is_monetized else 'passive'
    warning_text = translations[lang_code]['warn_monetization'] if not is_monetized else ""

    grade = calculate_grade(sub_count, view_count, video_count)

    return {
        'title': snippet['title'],
        'desc': snippet['description'][:100] + "...",
        'avatar': snippet['thumbnails']['medium']['url'],
        'banner': info['brandingSettings']['image'].get('bannerExternalUrl', '') if 'image' in info['brandingSettings'] else '',
        'sub_count': format_number(sub_count),
        'view_count': format_number(view_count),
        'video_count': format_number(video_count),
        'grade': grade,
        'niche': niche_name,
        'upload_schedule': peak_hour_str,
        'tags': keywords,
        'monetized': is_monetized,
        'status_key': status_key,
        'warning_text': warning_text,
        'earnings': earnings_str,
        'videos': videos
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    lang = request.args.get('lang', 'tr')
    if lang not in translations: lang = 'tr'
    content = translations[lang]
    
    result = None
    error = None

    if request.method == 'POST':
        query = request.form.get('query')
        if query:
            try:
                result = get_channel_data(query, lang)
                if not result: error = content['error']
            except Exception as e:
                print(f"Hata: {e}")
                error = "API Hatası veya Kota Doldu"

    return render_template('index.html', content=content, current_lang=lang, result=result, error=error)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
