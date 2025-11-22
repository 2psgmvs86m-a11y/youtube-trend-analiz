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

# --- PROXY HAVUZU (SENİN LİSTEN) ---
PROXIES = [
    "http://monrtwaa:066g1gqk2esk@216.10.27.159:6837",
    "http://monrtwaa:066g1gqk2esk@198.105.121.200:6462",
    "http://monrtwaa:066g1gqk2esk@198.23.239.134:6540",
    "http://monrtwaa:066g1gqk2esk@142.111.67.146:5611",
    "http://monrtwaa:066g1gqk2esk@142.111.48.253:7030"
]
# -----------------------------------

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
        'one_hit_label': 'Trend Durumu'
    },
    'en': {'title': 'YouTube Channel Auditor', 'error': 'Please enter a valid link!'},
    'de': {'title': 'YouTube-Kanal-Auditor', 'error': 'Bitte gültigen Link eingeben!'}
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
    except: return "Bilinmiyor", 1

def calculate_grade(sub_count, view_count, video_count):
    if sub_count == 0: return "D"
    avg_views = view_count / video_count if video_count > 0 else 0
    engagement = (avg_views / sub_count) * 100 if sub_count > 0 else 0
    if sub_count > 1000000: return "A+"
    if engagement > 10: return "A"
    if engagement > 2: return "B"
    return "C"

def get_niche_cpm(tags, title, desc):
    return 2.00, "Genel"

# --- GELİŞMİŞ MONETIZATION KONTROLÜ ---
def check_real_monetization(channel_id, sub_count, view_count):
    """
    1. Proxy ile sayfa kaynağını tarar.
    2. Cookie enjekte ederek 'Consent' duvarını aşar.
    3. Eğer tarama başarısız olursa, İSTATİSTİKSEL TAHMİN kullanır.
    """
    url = f"https://www.youtube.com/channel/{channel_id}?hl=en" # İngilizce zorla
    
    try:
        proxy_url = random.choice(PROXIES)
        proxies = {"http": proxy_url, "https": proxy_url}
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
            # SİHİRLİ COOKIE: Google'a "Ben şartları kabul ettim, sayfayı göster" der.
            "Cookie": "CONSENT=YES+cb.20220301-11-p0.en+FX+419; SOCS=CAISNQgDEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjMwMTI0LjA2X3AxGgJlbiACGgYIgJ-NowY"
        }
        
        response = requests.get(url, headers=headers, proxies=proxies, timeout=8)
        text = response.text
        
        # 1. KESİN KANITLAR (Scraping)
        if '"key":"is_monetization_enabled","value":"true"' in text: return True
        if 'sponsorButtonRenderer' in text: return True # Katıl Butonu
        if 'merchandiseShelfRenderer' in text: return True # Ürün Rafı
        
        # 2. İSTATİSTİKSEL KORUMA (Scraping Bulamadıysa)
        # Eğer scraping bir şey bulamadıysa (veya sayfa yüklenmediyse) hemen "Kapalı" deme.
        # Eğer kanal büyükse (10k abone + 1M izlenme), %99 ihtimalle açıktır.
        if sub_count > 10000 and view_count > 1000000:
            return True
            
        return False # Hem kod yok, hem kanal küçük -> KAPALI

    except Exception as e:
        print(f"Scraping Hatası: {e}")
        # Hata durumunda da büyük kanalları koru
        if sub_count > 10000: return True
        return False
# --------------------------------------

def extract_strict_link(query):
    id_match = re.search(r'(?:channel/|videos/|user/)?(UC[\w-]{21}[AQgw])', query)
    if id_match: return 'id', id_match.group(1)
    handle_match = re.search(r'@([\w.-]+)', query)
    if handle_match: return 'forHandle', '@' + handle_match.group(1)
    return None, None

def get_channel_data(query, lang_code='tr'):
    if not YOUTUBE_API_KEY: raise Exception("API Key Yok!")

    query_type, query_value = extract_strict_link(query)
    if not query_type: return None 
    
    channel_id = None
    if query_type == 'id': channel_id = query_value
    elif query_type == 'forHandle':
        stats_url = f"https://www.googleapis.com/youtube/v3/channels?part=id&forHandle={query_value}&key={YOUTUBE_API_KEY}"
        stats_res = requests.get(stats_url).json()
        if stats_res.get('items'): channel_id = stats_res['items'][0]['id']
        else: return None

    if not channel_id: return None

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
    
    # --- HİBRİT KONTROL (Proxy + İstatistik) ---
    is_monetized = False
    if sub_count >= 1000:
        # Artık fonksiyona sub_count ve view_count da gönderiyoruz
        is_monetized = check_real_monetization(channel_id, sub_count, view_count)
    
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
                error = "API Hatası"

    return render_template('index.html', content=content, current_lang=lang, result=result, error=error)

# Test sayfası da içinde
@app.route('/test-proxy')
def test_proxy_page():
    results = []
    results.append("<h1>Proxy Performans Testi</h1><ul>")
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for i, proxy in enumerate(PROXIES):
        proxies_dict = {"http": proxy, "https": proxy}
        try:
            start = datetime.now()
            resp = requests.get("https://www.google.com", headers=headers, proxies=proxies_dict, timeout=5)
            duration = (datetime.now() - start).total_seconds()
            if resp.status_code == 200:
                results.append(f"<li style='color:green;'>Proxy {i+1}: ✅ ÇALIŞIYOR ({duration:.2f}sn)</li>")
            else:
                results.append(f"<li style='color:orange;'>Proxy {i+1}: ⚠️ HATA ({resp.status_code})</li>")
        except Exception as e:
            results.append(f"<li style='color:red;'>Proxy {i+1}: ❌ BOZUK ({str(e)})</li>")
            
    results.append("</ul>")
    return "".join(results)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
