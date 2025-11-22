import os
import requests
import json
import re
import random
from flask import Flask, render_template, request
from datetime import datetime
from collections import Counter

app = Flask(__name__)

# TEK API ANAHTARI
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')

# --- PROXY HAVUZU (GÖRÜNTÜDEN EKLENDİ) ---
PROXIES = [
    "http://monrtwaa:066g1gqk2esk@216.10.27.159:6837",
    "http://monrtwaa:066g1gqk2esk@198.105.121.200:6462",
    "http://monrtwaa:066g1gqk2esk@198.23.239.134:6540",
    "http://monrtwaa:066g1gqk2esk@142.111.67.146:5611",
    "http://monrtwaa:066g1gqk2esk@142.111.48.253:7030"
]
# -----------------------------------------

translations = {
    'tr': {
        'title': 'YouTube Kanal Denetçisi',
        'search_btn': 'KANALI DENETLE',
        'placeholder': 'Lütfen Kanal Linki Giriniz (youtube.com/@isim)...',
        'grade': 'Kanal Notu',
        'upload_schedule': 'Yükleme Saati',
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
        'error': 'Lütfen geçerli bir YouTube Linki girin! (İsimle arama kapalıdır)',
        'latest': 'Son Yüklemeler',
        'warn_monetization': 'Kanalın para kazanma durumu doğrulanamadı veya kapalı.',
        'country': 'Kanal Ülkesi',
        'age': 'Kanal Yaşı',
        'growth': 'Günlük Büyüme',
        'daily_sub': 'Abone/Gün',
        'hidden_content': 'Gizli/Silinen Video',
        'consistency': 'İstikrar Durumu',
        'one_hit_label': 'En Çok İzlenen Video'
    },
    'en': {
        'title': 'YouTube Channel Auditor',
        'search_btn': 'AUDIT CHANNEL',
        'placeholder': 'Please Enter Channel Link (youtube.com/@name)...',
        'grade': 'Channel Grade',
        'upload_schedule': 'Upload Time',
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
        'error': 'Please enter a valid YouTube Link!',
        'latest': 'Latest Uploads',
        'warn_monetization': 'Monetization status could not be verified or is disabled.',
        'country': 'Channel Country',
        'age': 'Channel Age',
        'growth': 'Daily Growth',
        'daily_sub': 'Subs/Day',
        'hidden_content': 'Hidden/Deleted Videos',
        'consistency': 'Consistency Score',
        'one_hit_label': 'Most Viewed Video'
    },
    'de': {
        'title': 'YouTube-Kanal-Auditor',
        'search_btn': 'KANAL PRÜFEN',
        'placeholder': 'Bitte Kanallink eingeben...',
        'grade': 'Kanalnote',
        'upload_schedule': 'Upload-Zeit',
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
        'error': 'Bitte gültigen YouTube-Link eingeben!',
        'latest': 'Neueste Uploads',
        'warn_monetization': 'Monetarisierungsstatus konnte nicht überprüft werden.',
        'country': 'Land',
        'age': 'Kanalalter',
        'growth': 'Tägliches Wachstum',
        'daily_sub': 'Abos/Tag',
        'hidden_content': 'Versteckte Videos',
        'consistency': 'Konsistenz',
        'one_hit_label': 'Meistgesehenes Video'
    }
}

def format_number(num):
    if num > 1000000: return f"{num/1000000:.1f}M"
    if num > 1000: return f"{num/1000:.1f}K"
    return str(num)

def get_country_multiplier(country_code):
    high_cpm = ['US', 'GB', 'CA', 'AU', 'DE', 'CH', 'NO', 'SE']
    mid_cpm = ['FR', 'IT', 'ES', 'NL', 'KR', 'JP', 'AE']
    if country_code in high_cpm: return 3.0
    if country_code in mid_cpm: return 1.5
    return 0.8

def calculate_age_stats(published_at):
    try:
        pub_date = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
        now = datetime.now()
        diff = now - pub_date
        days_active = diff.days
        years = days_active // 365
        months = (days_active % 365) // 30
        age_str = f"{years} Yıl, {months} Ay" if years > 0 else f"{months} Ay"
        return age_str, days_active
    except:
        return "Bilinmiyor", 1

def calculate_grade(sub_count, view_count, video_count):
    if sub_count == 0 or video_count == 0: return "D"
    avg_views = view_count / video_count
    engagement_rate = (avg_views / sub_count) * 100 if sub_count > 0 else 0
    score = 0
    if sub_count >= 1000000: score += 30
    elif sub_count >= 500000: score += 25
    elif sub_count >= 100000: score += 20
    elif sub_count >= 10000: score += 10
    elif sub_count >= 1000: score += 5
    if engagement_rate >= 20: score += 50
    elif engagement_rate >= 10: score += 40
    elif engagement_rate >= 5: score += 30
    elif engagement_rate >= 2: score += 20
    elif engagement_rate >= 1: score += 10
    else: score += 5
    if video_count >= 1000: score += 20
    elif video_count >= 300: score += 15
    elif video_count >= 50: score += 10
    else: score += 5
    if sub_count < 1000 and score > 60: score = 60
    if score >= 90: return "A+"
    if score >= 80: return "A"
    if score >= 65: return "B+"
    if score >= 50: return "B"
    if score >= 35: return "C"
    return "D"

# --- PROXY DESTEKLİ MONETIZATION KONTROLÜ ---
def check_real_monetization(channel_id):
    try:
        url = f"https://www.youtube.com/channel/{channel_id}"
        
        # 1. Rastgele Proxy Seç
        proxy_url = random.choice(PROXIES)
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        # 2. Tarayıcı Kimliği (User-Agent)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/"
        }
        
        # 3. İsteği Gönder (Timeout 6 saniye)
        response = requests.get(url, headers=headers, proxies=proxies, timeout=6)
        text = response.text
        
        # 4. Kaynak Kodunu Tara
        if '"key":"is_monetization_enabled","value":"true"' in text: return True
        if 'sponsorButtonRenderer' in text: return True
        if 'merchandiseShelfRenderer' in text: return True
        if 'is_monetization_enabled' in text and 'true' in text: return True
        
        return False
    except Exception as e:
        # Proxy hatası olursa sessizce 'False' dön (Site çökmesin)
        print(f"Proxy Bağlantı Hatası: {e}")
        return False 
# --------------------------------------------

def get_niche_cpm(tags_list, title, desc):
    full_text = " ".join(tags_list).lower() + " " + title.lower() + " " + desc.lower()
    finance_keys = ['finance', 'crypto', 'bitcoin', 'money', 'business', 'finans', 'para', 'borsa']
    tech_keys = ['tech', 'review', 'phone', 'apple', 'teknoloji', 'inceleme', 'yazılım', 'coding']
    game_keys = ['game', 'gaming', 'play', 'minecraft', 'roblox', 'oyun', 'pubg', 'valorant']
    vlog_keys = ['vlog', 'life', 'daily', 'eğlence', 'challenge']
    news_keys = ['news', 'haber', 'siyaset', 'politics']
    if any(word in full_text for word in finance_keys): return 8.00, "Finans / Ekonomi 💰"
    elif any(word in full_text for word in tech_keys): return 4.50, "Teknoloji / Eğitim 💻"
    elif any(word in full_text for word in game_keys): return 1.20, "Gaming / Oyun 🎮"
    elif any(word in full_text for word in vlog_keys): return 2.00, "Eğlence / Vlog 🎬"
    elif any(word in full_text for word in news_keys): return 1.50, "Haber / Gündem 📰"
    return 2.00, "Genel / Karma 🌍"

# --- SIKI KONTROL: SADECE LİNK ---
def extract_strict_link(query):
    id_match = re.search(r'(?:channel/|videos/|user/)?(UC[\w-]{21}[AQgw])', query)
    if id_match: return 'id', id_match.group(1)
    
    handle_match = re.search(r'@([\w.-]+)', query)
    if handle_match: return 'forHandle', '@' + handle_match.group(1)
        
    return None, None
# ---------------------------------

def get_channel_data(query, lang_code='tr'):
    if not YOUTUBE_API_KEY: raise Exception("API Key Yok!")

    # 1. TÜR TESPİTİ (Sadece Link)
    query_type, query_value = extract_strict_link(query)
    if not query_type: return None 
    
    channel_id = None
    
    if query_type == 'id':
        channel_id = query_value
    elif query_type == 'forHandle':
        stats_url = f"https://www.googleapis.com/youtube/v3/channels?part=id&forHandle={query_value}&key={YOUTUBE_API_KEY}"
        stats_res = requests.get(stats_url).json()
        if stats_res.get('items'): channel_id = stats_res['items'][0]['id']
        else: return None

    if not channel_id: return None

    # 2. İSTATİSTİKLER
    stats_url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics,snippet,contentDetails,brandingSettings&id={channel_id}&key={YOUTUBE_API_KEY}"
    stats_res = requests.get(stats_url).json()
    
    if 'items' not in stats_res: return None

    info = stats_res['items'][0]
    stats = info['statistics']
    snippet = info['snippet']

    sub_count = int(stats.get('subscriberCount', 0))
    view_count = int(stats.get('viewCount', 0))
    video_count = int(stats.get('videoCount', 0))
    
    country_code = snippet.get('country', 'TR')
    age_str, days_active = calculate_age_stats(snippet.get('publishedAt', ''))
    daily_subs = int(sub_count / days_active) if days_active > 0 else 0
    
    keywords = []
    if 'brandingSettings' in info and 'channel' in info['brandingSettings']:
        keys = info['brandingSettings']['channel'].get('keywords', '')
        if keys: keywords = [k.replace('"', '') for k in keys.split(' ')[:10]]

    uploads_id = info['contentDetails']['relatedPlaylists']['uploads']
    
    # 3. VİDEOLAR & GİZLİ İÇERİK
    videos_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet,contentDetails&playlistId={uploads_id}&maxResults=10&key={YOUTUBE_API_KEY}"
    videos_res = requests.get(videos_url).json()

    playlist_total = videos_res.get('pageInfo', {}).get('totalResults', 0)
    hidden_videos = max(0, playlist_total - video_count)

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

    # Trend / İstikrar Analizi (Sorgusuz)
    consistency_label = "Stabil"
    if daily_subs > 500: consistency_label = "Yükselişte 🚀"
    elif daily_subs < 0: consistency_label = "Düşüşte 📉"
    consistency_data = {'label': consistency_label, 'top_video_views': "Veri Yok"}

    peak_hour_str = "Belirsiz"
    if upload_hours:
        common_hour = Counter(upload_hours).most_common(1)[0][0]
        tr_hour = (common_hour + 3) % 24
        peak_hour_str = f"{tr_hour}:00 - {tr_hour+1}:00 (TR)"

    base_cpm, niche_name = get_niche_cpm(keywords, snippet['title'], snippet['description'])
    country_multiplier = get_country_multiplier(country_code)
    final_cpm = base_cpm * country_multiplier
    est_monthly_views = view_count * 0.03 
    monthly_rev = (est_monthly_views / 1000) * final_cpm
    
    # --- MONETIZATION KONTROLÜ ---
    is_monetized = False
    if sub_count >= 1000:
        # Proxy üzerinden gerçek kontrol yap
        scraping_result = check_real_monetization(channel_id)
        if scraping_result:
            is_monetized = True
        else:
            # Proxy başarısız olsa bile büyük kanalları koru
            if sub_count > 5000 and view_count > 100000: is_monetized = True
            else: is_monetized = False
    
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
        'videos': videos,
        'country': country_code,
        'age': age_str,
        'daily_subs': daily_subs,
        'hidden_videos': hidden_videos,
        'consistency': consistency_data
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
                error = "Sistem yoğun veya proxy hatası."

    return render_template('index.html', content=content, current_lang=lang, result=result, error=error)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
