import os
import requests
import json
import re
import random
from flask import Flask, render_template, request, session, redirect, url_for
from datetime import datetime
from collections import Counter

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key_change_me')

# API Anahtarları
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY') 

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
        'consistency': 'İstikrar Durumu',
        'seo_score': 'SEO Skoru',
        'video_title_len': 'Başlık Uzunluğu',
        'video_tag_count': 'Etiket Sayısı',
        'video_desc_len': 'Açıklama Uzunluğu',
        'keyword_match': 'Başlık/Etiket Uyumu',
        'video_views': 'Görüntülenme',
        'video_likes': 'Beğenme',
        'video_comments': 'Yorum'
    },
    'en': { 'title': 'YouTube Channel Auditor', 'error': 'Invalid Link', 'active': 'ACTIVE', 'passive': 'INACTIVE' },
    'de': { 'title': 'YouTube-Kanal-Auditor', 'error': 'Ungültiger Link', 'active': 'AKTIV', 'passive': 'INAKTIV' }
}

def format_number(num):
    if num > 1000000: return f"{num/1000000:.1f}M"
    if num > 1000: return f"{num/1000:.1f}K"
    return str(num)

def get_grade_value(grade):
    grade_map = {'A+': 5, 'A': 4, 'B+': 3, 'B': 2, 'C': 1, 'D': 0}
    return grade_map.get(grade, 0)

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

def get_country_multiplier(country_code):
    high_cpm = ['US', 'GB', 'CA', 'AU', 'DE', 'CH', 'NO', 'SE']
    if country_code in high_cpm: return 3.0
    return 0.8

def calculate_age_stats(published_at):
    try:
        pub_date = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
        now = datetime.now()
        diff = now - pub_date
        days_active = diff.days
        years = diff.days // 365
        months = (diff.days % 365) // 30
        return f"{years} Yıl, {months} Ay", days_active
    except: return "Bilinmiyor", 1

def check_real_monetization(channel_id):
    return True 

def extract_strict_link(query):
    id_match = re.search(r'(?:channel/|videos/|user/)?(UC[\w-]{21}[AQgw])', query)
    if id_match: return 'id', id_match.group(1)
    handle_match = re.search(r'@([\w.-]+)', query)
    if handle_match: return 'forHandle', '@' + handle_match.group(1)
    return None, None

def extract_video_id(query):
    match = re.search(r'(?:youtu\.be\/|v=|embed\/)([\w-]{11})', query)
    if match: return match.group(1)
    if re.match(r'^[\w-]{11}$', query): return query
    return None

# --- GROQ API İLE İÇERİK OLUŞTURMA (DÜZELTİLMİŞ PARSING) ---
def generate_ai_content(topic, style):
    if not GROQ_API_KEY:
        return {"error": "GROQ_API_KEY Render'da tanımlı değil."}
    
    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    
    system_prompt = "Sen, profesyonel bir YouTube SEO uzmanısın. Cevabını kesinlikle şu formatta ver:\nBAŞLIKLAR:\n1. Başlık\n2. Başlık\n3. Başlık\n\nAÇIKLAMA:\n(Buraya açıklama metni gelecek)"
    
    user_prompt = f"Konu: {topic}. Stil: {style}. Türkçe, 3 viral başlık ve 50-60 kelimelik profesyonel açıklama yaz."

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {GROQ_API_KEY}'
    }

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 800
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status() 
        data = response.json()
        
        if data.get('choices'):
            generated_text = data['choices'][0]['message']['content']
            
            # YENİ PARSING MANTIĞI: Anahtar kelimelerle böl
            titles = []
            description = "Açıklama oluşturulamadı."
            
            if "AÇIKLAMA:" in generated_text:
                parts = generated_text.split("AÇIKLAMA:")
                titles_part = parts[0].replace("BAŞLIKLAR:", "").strip()
                description = parts[1].strip()
                
                # Başlıkları satır satır al
                titles = [t.strip() for t in titles_part.split('\n') if t.strip()]
            else:
                # Yedek plan (Eski usul)
                description = generated_text
            
            return {
                "titles": titles[:3],
                "description": description,
                "raw": generated_text
            }

        return {"error": "Yapay Zeka Metin Üretemedi (Boş Cevap)"}

    except requests.exceptions.RequestException:
        return {"error": f"API Bağlantı Hatası: Groq Kota/Faturalandırma Sorunu."}
    except Exception:
        return {"error": "Bir sorun oluştu. Lütfen girdilerinizi kontrol edin."}

def get_video_data(video_id, lang_code='tr'):
    if not YOUTUBE_API_KEY: return None
    video_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id={video_id}&key={YOUTUBE_API_KEY}"
    video_res = requests.get(video_url).json()
    if 'items' not in video_res or not video_res['items']: return None
    item = video_res['items'][0]
    snippet = item['snippet']
    stats = item['statistics']
    title = snippet.get('title', '')
    description = snippet.get('description', '')
    tags = snippet.get('tags', [])
    view_count = int(stats.get('viewCount', 0))
    like_count = int(stats.get('likeCount', 0))
    comment_count = int(stats.get('commentCount', 0))
    score = 0
    title_len = len(title)
    if 40 <= title_len <= 70: score += 20 
    elif 30 <= title_len <= 80: score += 10
    tag_count = len(tags)
    if 10 <= tag_count <= 15: score += 30
    elif 5 <= tag_count <= 20: score += 20
    elif tag_count > 0: score += 10
    desc_len = len(description)
    if desc_len >= 150: score += 20
    elif desc_len >= 50: score += 10
    keywords_in_title_desc = 0
    for tag in tags:
        if tag.lower() in title.lower() or tag.lower() in description.lower():
            keywords_in_title_desc += 1
    if keywords_in_title_desc >= 3: score += 30
    elif keywords_in_title_desc >= 1: score += 15
    final_score = min(score, 100) 
    engagement = (like_count + comment_count) / view_count * 100 if view_count > 0 else 0
    status_label = "Mükemmel" if final_score >= 80 else "İyi" if final_score >= 50 else "Geliştirilmeli"
    recommendation_text = ""
    if title_len < 40 or title_len > 70: recommendation_text += "Başlık uzunluğunu 40-70 karakter yapın. "
    if tag_count < 10: recommendation_text += "Daha fazla etiket ekleyin. "
    return {
        'title': title, 'channel_title': snippet.get('channelTitle', 'N/A'), 'thumbnail': snippet['thumbnails']['high']['url'],
        'tags': tags, 'view_count': format_number(view_count), 'like_count': format_number(like_count),
        'comment_count': format_number(comment_count), 'engagement': f"{engagement:.2f}%", 'seo_score': final_score,
        'status': status_label, 'recommendation': recommendation_text or "Harika iş!", 'title_len': title_len,
        'tag_count': tag_count, 'desc_len': desc_len, 'keyword_match': keywords_in_title_desc
    }

def get_channel_data(query, lang_code='tr'):
    if not YOUTUBE_API_KEY: return None 
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
    daily_subs_raw = int(sub_count / days_active) if days_active > 0 else 0
    daily_subs_formatted = format_number(daily_subs_raw)
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
            videos.append({ 'title': item['snippet']['title'], 'thumb': item['snippet']['thumbnails']['high']['url'], 'id': item['snippet']['resourceId']['videoId'], 'published': dt.strftime("%d.%m.%Y") })
    total_analyzed = shorts_count + long_videos_count
    channel_type_label = "Belirsiz"
    if total_analyzed > 0:
        shorts_ratio = (shorts_count / total_analyzed) * 100
        if shorts_ratio > 60: channel_type_label = "Shorts Ağırlıklı 📱"
        elif shorts_ratio < 20: channel_type_label = "Uzun Video 🎥"
        else: channel_type_label = "Karışık / Dengeli ⚖️"
    consistency_label = "Stabil"
    if daily_subs_raw > 500: consistency_label = "Yükselişte 🚀"
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
    is_monetized = sub_count >= 1000 and view_count > 4000
    earnings_str = f"${monthly_rev * 0.8:,.0f} - ${monthly_rev * 1.2:,.0f}" if is_monetized else "$0"
    status_key = 'active' if is_monetized else 'passive'
    warning_text = translations[lang_code]['warn_monetization'] if not is_monetized else ""
    grade = calculate_grade(sub_count, view_count, video_count)
    return {
        'title': snippet['title'], 'desc': snippet['description'][:100], 'avatar': snippet['thumbnails']['medium']['url'],
        'sub_count': format_number(sub_count), 'view_count': format_number(view_count), 'video_count': format_number(video_count),
        'grade': grade, 'niche': niche_name, 'upload_schedule': peak_hour_str, 'tags': keywords,
        'monetized': is_monetized, 'status_key': status_key, 'warning_text': warning_text, 'earnings': earnings_str,
        'videos': videos, 'country': country_code, 'age': age_str, 
        'daily_subs': daily_subs_formatted, 'channel_type': channel_type_label, 'hidden_videos': hidden_videos, 'consistency': consistency_data,
        'raw_sub_count': sub_count, 'raw_view_count': view_count, 'raw_video_count': video_count, 'raw_daily_subs': daily_subs_raw, 'raw_earnings_high': monthly_rev * 1.2, 'raw_grade_val': get_grade_value(grade), 'name': snippet['title'], 'avatar': snippet['thumbnails']['medium']['url'] 
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
            except Exception as e: error = "Sunucu hatası."
    return render_template('index.html', content=content, current_lang=lang, result=result, error=error)

@app.route('/araclar/kanal-karsilastir', methods=['GET', 'POST'])
def channel_vs():
    results = {}
    error = None
    lang = request.args.get('lang', 'tr')
    content = translations.get(lang, translations['tr'])
    input_data = {'query1': '', 'query2': ''}
    if request.method == 'POST':
        query1 = request.form.get('query1')
        query2 = request.form.get('query2')
        input_data = {'query1': query1, 'query2': query2}
        try:
            data1 = get_channel_data(query1, lang)
            data2 = get_channel_data(query2, lang)
            if not data1 or not data2: error = f"Veri alınamadı."
            else:
                results = { 'name1': data1['title'], 'name2': data2['title'], 'subs1': data1['sub_count'], 'subs2': data2['sub_count'], 'views1': data1['view_count'], 'views2': data2['view_count'], 'videos1': data1['video_count'], 'videos2': data2['video_count'], 'grade1': data1['grade'], 'grade2': data2['grade'], 'daily_subs1': data1['daily_subs'], 'daily_subs2': data2['daily_subs'], 'earnings1': data1['earnings'], 'earnings2': data2['earnings'], 'country1': data1['country'], 'country2': data2['country'], 'avatar1': data1['avatar'], 'avatar2': data2['avatar'] }
        except Exception: error = "Kıyaslama hatası."
    return render_template('channel_vs.html', content=content, result=results, error=error, input_data=input_data, current_lang=lang)

@app.route('/araclar/ai-baslik', methods=['GET', 'POST'])
def ai_generator():
    ai_result = None
    input_data = {}
    error_message = None
    MAX_USES = 5
    if 'ai_uses' not in session: session['ai_uses'] = 0
    if request.method == 'POST':
        topic = request.form.get('topic')
        style = request.form.get('style')
        captcha_check = request.form.get('captcha_check')
        captcha_result = session.pop('captcha_result', None) 
        if not topic or not style: error_message = "Eksik bilgi."
        elif captcha_result is None or str(captcha_result) != captcha_check: error_message = "Hatalı CAPTCHA."
        elif session['ai_uses'] >= MAX_USES: error_message = "Limit doldu."
        else:
            ai_result = generate_ai_content(topic, style)
            input_data = {'topic': topic, 'style': style}
            if 'error' not in ai_result: session['ai_uses'] += 1
            else: error_message = ai_result['error'] 
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    captcha_question = f"{num1} + {num2} = ?"
    session['captcha_result'] = num1 + num2 
    uses_left = MAX_USES - session.get('ai_uses', 0)
    content = translations.get(request.args.get('lang', 'tr'), translations['tr'])
    return render_template('ai_tool.html', content=content, ai_result=ai_result, input_data=input_data, error=error_message, captcha_question=captcha_question, uses_left=uses_left, max_uses=MAX_USES, current_lang=request.args.get('lang', 'tr'))

@app.route('/araclar/video-seo', methods=['GET', 'POST'])
def video_seo():
    result = None
    error = None
    lang = request.args.get('lang', 'tr')
    content = translations.get(lang, translations['tr'])
    if request.method == 'POST':
        query = request.form.get('query')
        video_id = extract_video_id(query)
        if not video_id: error = "Geçersiz video linki."
        else:
            try:
                result = get_video_data(video_id, lang)
                if not result: error = "Video verisi alınamadı."
            except Exception: error = "Sunucu hatası."
    return render_template('video_seo.html', content=content, result=result, error=error, current_lang=lang)

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


