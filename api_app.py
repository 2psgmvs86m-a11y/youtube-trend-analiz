import os
import requests
from flask import Flask, render_template, request
from datetime import datetime
from collections import Counter

app = Flask(__name__)

# API Anahtarı
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')

translations = {
    'tr': {
        'title': 'YouTube Kanal Denetçisi',
        'search_btn': 'Kanali Denetle',
        'placeholder': 'Kanal Adı veya Linki...',
        'grade': 'Kanal Notu',
        'upload_schedule': 'Video Yükleme Saati',
        'tags': 'Kanal Etiketleri',
        'category': 'Tahmini Kategori',
        'monetization': 'Para Kazanma',
        'earnings': 'Tahmini Aylık Gelir',
        'active': 'AÇIK ✅',
        'passive': 'KAPALI ❌',
        'subs': 'Abone',
        'views': 'Görüntülenme',
        'videos': 'Video',
        'engagement': 'Etkileşim Oranı',
        'error': 'Kanal bulunamadı!',
        'latest': 'Son Yüklemeler'
    },
    'en': {
        'title': 'YouTube Channel Auditor',
        'search_btn': 'Audit Channel',
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
        'latest': 'Latest Uploads'
    },
    'de': {
        'title': 'YouTube-Kanal-Auditor',
        'search_btn': 'Kanal prüfen',
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
        'latest': 'Neueste Uploads'
    }
}

def format_number(num):
    if num > 1000000: return f"{num/1000000:.1f}M"
    if num > 1000: return f"{num/1000:.1f}K"
    return str(num)

def calculate_grade(sub_count, view_count, video_count):
    if sub_count == 0 or video_count == 0: return "D"
    
    avg_views = view_count / video_count
    engagement = (avg_views / sub_count) * 100 if sub_count > 0 else 0

    if sub_count > 1000000 and engagement > 2: return "A+"
    if sub_count > 500000 and engagement > 3: return "A"
    if engagement > 10: return "A"
    if engagement > 5: return "B+"
    if engagement > 2: return "B"
    if engagement > 1: return "C"
    return "D"

def get_niche_cpm(tags_list, title, desc):
    # HATA BURADAYDI - DÜZELTİLDİ
    full_text = " ".join(tags_list).lower() + " " + title.lower() + " " + desc.lower()
    
    finance_keys = ['finance', 'crypto', 'bitcoin', 'money', 'business', 'finans', 'para', 'borsa']
    tech_keys = ['tech', 'review', 'phone', 'apple', 'teknoloji', 'inceleme', 'yazılım']
    game_keys = ['game', 'gaming', 'play', 'minecraft', 'roblox', 'oyun', 'pubg']
    vlog_keys = ['vlog', 'life', 'daily', 'eğlence', 'challenge']
    news_keys = ['news', 'haber', 'siyaset']

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

def get_channel_data(query):
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
    earnings_str = f"${monthly_rev * 0.8:,.0f} - ${monthly_rev * 1.2:,.0f}"

    is_monetized = sub_count >= 1000 and view_count > 50000

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
                result = get_channel_data(query)
                if not result: error = content['error']
            except Exception as e:
                print(e)
                error = "API Hatası / Veri Çekilemedi"

    return render_template('index.html', content=content, current_lang=lang, result=result, error=error)

if __name__ == '__main__':
    app.run(debug=True)
