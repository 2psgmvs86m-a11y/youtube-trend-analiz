import os
import requests
import json
import re
from flask import Flask, render_template, request, session, redirect, url_for
from datetime import datetime
from collections import Counter

# Yeni Kütüphaneler:
from google.auth.transport.requests import Request
from google.oauth2 import service_account

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key_change_me')

# API Anahtarları
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
# JSON dosyasını ortam değişkeninden çekiyoruz (GEMINI_SERVICE_ACCOUNT_JSON)
SERVICE_ACCOUNT_JSON = os.environ.get('GEMINI_SERVICE_ACCOUNT_JSON') 

# --- GEMINI YETKİLENDİRME (CREDENTIALS) KONTROLÜ ---
GEMINI_CREDENTIALS = None
if SERVICE_ACCOUNT_JSON:
    try:
        # JSON string'i yükleyip Service Account Credential'a çeviriyoruz
        info = json.loads(SERVICE_ACCOUNT_JSON)
        # Gerekli scope'u (izin kapsamı) tanımlıyoruz
        SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
        GEMINI_CREDENTIALS = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    except Exception as e:
        print(f"!!! GEMINI JSON YÜKLEME HATASI: {e} !!!")

# --- GLOBAL ERİŞİM TOKEN'I YÖNETİMİ ---
# Tokenlar belli bir süre sonra sona erer, bu yüzden sürekli yenilememiz gerekir
def get_access_token():
    if not GEMINI_CREDENTIALS:
        return None
    
    if not GEMINI_CREDENTIALS.valid:
        # Token süresi dolduysa yenile
        GEMINI_CREDENTIALS.refresh(Request())
    
    return GEMINI_CREDENTIALS.token
# ----------------------------------------------------

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
        'error': 'Lütfen geçerli bir YouTube Linki girin!',
        'latest': 'Son Yüklemeler',
        'warn_monetization': 'Kanalın para kazanma durumu doğrulanamadı veya kapalı.',
        'country': 'Kanal Ülkesi',
        'age': 'Kanal Yaşı',
        'growth': 'Günlük Büyüme',
        'daily_sub': 'Abone/Gün',
        'channel_type': 'Kanal Tipi',
        'consistency': 'İstikrar Durumu'
    },
    'en': { 'title': 'YouTube Channel Auditor', 'error': 'Invalid Link', 'active': 'ACTIVE', 'passive': 'INACTIVE' },
    'de': { 'title': 'YouTube-Kanal-Auditor', 'error': 'Ungültiger Link', 'active': 'AKTIV', 'passive': 'INAKTIV' }
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
        return f"{years} Yıl, {months} Ay", days_active
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
    full_text = (title + " " + desc).lower()
    if "finance" in full_text or "para" in full_text: return 8.00, "Finans"
    return 2.00, "Genel"

def parse_duration(duration_str):
    match = re.match(r'PT(\d+H)?(\d+M)?(\d+S)?', duration_str)
    if not match: return 0
    hours = int(match.group(1)[:-1]) if match.group(1) else 0
    minutes = int(match.group(2)[:-1]) if match.group(2) else 0
    seconds = int(match.group(3)[:-1]) if match.group(3) else 0
    return (hours * 3600) + (minutes * 60) + seconds

def check_real_monetization(channel_id):
    url = f"https://www.youtube.com/channel/{channel_id}?hl=en"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "en-US,en;q=0.9",
            "Cookie": "CONSENT=YES+cb.20210328-17-p0.en+FX+419; SOCS=CAISNQgDEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjMwMTI0LjA2X3AxGgJlbiACGgYIgJ-NowY"
        }
        response = requests.get(url, headers=headers, timeout=5)
        text = response.text
        
        if '"key":"is_monetization_enabled","value":"true"' in text: return True
        if 'sponsorButtonRenderer' in text: return True
        if 'merchandiseShelfRenderer' in text: return True
        
        return False
    except: return False

def extract_strict_link(query):
    id_match = re.search(r'(?:channel/|videos/|user/)?(UC[\w-]{21}[AQgw])', query)
    if id_match: return 'id', id_match.group(1)
    handle_match = re.search(r'@([\w.-]+)', query)
    if handle_match: return 'forHandle', '@' + handle_match.group(1)
    return None, None

# --- HARİCİ GEMINI API İLE İÇERİK OLUŞTURMA (DÜŞÜNEBİLEN MOD) ---
def generate_ai_content(topic, style):
    access_token = get_access_token()
    if not access_token:
        return {"error": "Hata: Gemini Yetkilendirme Başarısız. JSON verinizi ve Google yetkilerini kontrol edin."}
    
    prompt = f"Konu: {topic}. Stil: {style}. Bu bilgilere dayanarak YouTube için 3 adet kısa, viral başlık ve 1 adet 150 kelimelik ilgi çekici açıklama metni oluştur. Başlıkları madde madde ayır."
    
    # API URL'si artık KEY yerine Service Account ile çalışıyor
    API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}' # Erişim token'ı kullanılıyor
    }

    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'config': {
            'temperature': 0.8
        }
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status() 
        data = response.json()
        
        if data.get('candidates'):
            generated_text = data['candidates'][0]['content']['parts'][0]['text']
            
            parts = generated_text.split('\n')
            titles = [p.strip() for p in parts if p.strip() and p.strip().startswith(('1.', '2.', '3.', '-', '*'))]
            description = "\n".join([p for p in parts if not p.strip().startswith(('1.', '2.', '3.', '-', '*'))]).strip()

            return {
                "titles": titles[:3],
                "description": description if description else generated_text,
                "raw": generated_text
            }

        return {"error": "Yapay Zeka Metin Üretemedi (Boş Cevap)"}

    except requests.exceptions.RequestException as e:
        return {"error": f"API Bağlantı Hatası: Kota/Faturalandırma Sorunu. Gemini panelinizi kontrol edin."}
    except Exception:
        return {"error": "Bir sorun oluştu. Lütfen girdilerinizi kontrol edin."}


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
    
    shorts_count = 0
    long_videos_count = 0
    
    for item in videos_res.get('items', []):
        pub_time = item['snippet']['publishedAt']
        dt = datetime.strptime(pub_time, "%Y-%m-%dT%H:%M:%SZ")
        upload_hours.append(dt.hour)
        
        duration_str = item['contentDetails'].get('duration', 'PT0S')
        seconds = parse_duration(duration_str)
        
        if seconds <= 60: shorts_count += 1
        else: long_videos_count += 1

        if len(videos) < 3:
            videos.append({
                'title': item['snippet']['title'],
                'thumb': item['snippet']['thumbnails']['high']['url'],
                'id': item['snippet']['resourceId']['videoId'],
                'published': dt.strftime("%d.%m.%Y")
            })

    total_analyzed = shorts_count + long_videos_count
    channel_type_label = "Belirsiz"
    if total_analyzed > 0:
        shorts_ratio = (shorts_count / total_analyzed) * 100
        if shorts_ratio > 60: channel_type_label = "Shorts Ağırlıklı 📱"
        elif shorts_ratio < 20: channel_type_label = "Uzun Video 🎥"
        else: channel_type_label = "Karışık / Dengeli ⚖️"
    
    consistency_label = "Stabil"
    if daily_subs > 500: consistency_label = "Yükselişte 🚀"
    consistency_data = {'label': consistency_label}
    
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
    
    is_monetized = False
    if sub_count >= 1000:
        scraping_result = check_real_monetization(channel_id)
        if scraping_result: is_monetized = True
        else:
            if sub_count > 5000 and view_count > 500000: is_monetized = True
            else: is_monetized = False
    
    earnings_str = f"${monthly_rev * 0.8:,.0f} - ${monthly_rev * 1.2:,.0f}" if is_monetized else "$0"
    status_key = 'active' if is_monetized else 'passive'
    warning_text = translations[lang_code]['warn_monetization'] if not is_monetized else ""
    grade = calculate_grade(sub_count, view_count, video_count)

    return {
        'title': snippet['title'], 'desc': snippet['description'][:100], 'avatar': snippet['thumbnails']['medium']['url'],
        'sub_count': format_number(sub_count), 'view_count': format_number(view_count), 'video_count': format_number(video_count),
        'grade': grade, 'niche': niche_name, 'upload_schedule': peak_hour_str, 'tags': keywords,
        'monetized': is_monetized, 'status_key': status_key, 'warning_text': warning_text, 'earnings': earnings_str,
        'videos': videos, 'country': country_code, 'age': age_str, 'daily_subs': daily_subs, 'channel_type': channel_type_label,
        'hidden_videos': hidden_videos, 'consistency': consistency_data
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
                error = "Sunucu hatası oluştu."

    return render_template('index.html', content=content, current_lang=lang, result=result, error=error)

@app.route('/araclar/ai-baslik', methods=['GET', 'POST'])
def ai_generator():
    ai_result = None
    input_data = {}
    
    if request.method == 'POST':
        topic = request.form.get('topic')
        style = request.form.get('style')
        
        if topic and style:
            # Yapay Zeka motorunu çağırın
            ai_result = generate_ai_content(topic, style)
            input_data = {'topic': topic, 'style': style}

    return render_template('ai_tool.html', ai_result=ai_result, input_data=input_data)

@app.route('/gizlilik')
def privacy(): return render_template('privacy.html', page_key='privacy')
@app.route('/kullanim')
def terms(): return render_template('privacy.html', page_key='terms')
@app.route('/hakkimizda')
def about(): return render_template('privacy.html', page_key='about')
@app.route('/iletisim')
def contact(): return render_template('privacy.html', page_key='contact')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
