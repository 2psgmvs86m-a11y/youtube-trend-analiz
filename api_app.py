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
    'en': { 'title': 'YouTube Audit', 'error': 'Invalid Link', 'active': 'ACTIVE', 'passive': 'INACTIVE' },
    'de': { 'title': 'YouTube Audit', 'error': 'Ungültiger Link', 'active': 'AKTIV', 'passive': 'INAKTIV' }
}

def format_number(num):
    if num is None: return "0"
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

# --- ANA KANAL VERİSİ ---
def get_channel_data(query, lang_code='tr'):
    if not YOUTUBE_API_KEY: return None 
    query_type, query_value = extract_strict_link(query)
    if not query_type: return None 
    
    channel_id = None
    if query_type == 'id': channel_id = query_value
    elif query_type == 'forHandle':
        try:
            stats_url = f"https://www.googleapis.com/youtube/v3/channels?part=id&forHandle={query_value}&key={YOUTUBE_API_KEY}"
            stats_res = requests.get(stats_url).json()
            if stats_res.get('items'): channel_id = stats_res['items'][0]['id']
            else: return None
        except: return None

    if not channel_id: return None

    try:
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

        videos = []
        shorts_count = 0
        long_videos_count = 0
        
        if 'items' in videos_res:
            for item in videos_res.get('items', []):
                pub_time = item['snippet']['publishedAt']
                dt = datetime.strptime(pub_time, "%Y-%m-%dT%H:%M:%SZ")
                
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
        if daily_subs_raw > 500: consistency_label = "Yükselişte 🚀"
        consistency_data = {'label': consistency_label}
        
        base_cpm, niche_name = get_niche_cpm(keywords, snippet['title'], snippet['description'])
        final_cpm = base_cpm * 1.0 
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
            'grade': grade, 'niche': niche_name, 'upload_schedule': "Belirsiz", 'tags': keywords,
            'monetized': is_monetized, 'status_key': status_key, 'warning_text': warning_text, 'earnings': earnings_str,
            'videos': videos, 'country': country_code, 'age': age_str, 
            'daily_subs': daily_subs_formatted, 
            'channel_type': channel_type_label,
            'consistency': consistency_data,
            # --- KIYASLAMA İÇİN HAM VERİLER (CRITICAL FIX) ---
            'raw_sub_count': sub_count, 
            'raw_view_count': view_count, 
            'raw_video_count': video_count,
            'raw_daily_subs': daily_subs_raw, 
            'raw_earnings_high': monthly_rev * 1.2, 
            'raw_grade_val': get_grade_value(grade),
            'name': snippet['title'], 
            'avatar': snippet['thumbnails']['medium']['url'] 
        }
    except Exception as e:
        print(f"API Error: {e}")
        return None

# --- VİDEO SEO ---
def get_video_data(video_id, lang_code='tr'):
    if not YOUTUBE_API_KEY: return None
    try:
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
        keywords_match = 0
        for tag in tags:
            if tag.lower() in title.lower(): keywords_match += 1
        if keywords_match >= 1: score += 30
        final_score = min(score + keywords_match*5, 100)
        engagement = (like_count + comment_count) / view_count * 100 if view_count > 0 else 0
        status_label = "Mükemmel" if final_score >= 80 else "İyi" if final_score >= 50 else "Geliştirilmeli"
        return {
            'title': title, 'channel_title': snippet.get('channelTitle', ''), 'thumbnail': snippet['thumbnails']['high']['url'],
            'tags': tags, 'view_count': format_number(view_count), 'like_count': format_number(like_count),
            'comment_count': format_number(comment_count), 'engagement': f"{engagement:.2f}%", 'seo_score': final_score,
            'status': status_label, 'recommendation': "Meta verilerinizi optimize edin.",
            'title_len': title_len, 'tag_count': tag_count, 'desc_len': desc_len, 'keyword_match': keywords_match
        }
    except: return None

# --- GROQ AI ---
def generate_ai_content(topic, style):
    if not GROQ_API_KEY: return {"error": "GROQ_API_KEY Tanımsız"}
    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {GROQ_API_KEY}'}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": f"Konu: {topic}, Stil: {style}. Türkçe, 3 viral başlık ve 50 kelimelik açıklama yaz."}],
        "temperature": 0.7, "max_tokens": 500
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=15)
        data = response.json()
        if data.get('choices'):
            content = data['choices'][0]['message']['content']
            return {"description": content, "titles": ["Başlıklar açıklamada mevcuttur."]}
        return {"error": "AI Yanıt vermedi"}
    except: return {"error": "API Hatası"}

# --- ROTALAR ---
@app.route('/', methods=['GET', 'POST'])
def index():
    lang = request.args.get('lang', 'tr')
    content = translations.get(lang, translations['tr'])
    result = None
    error = None
    if request.method == 'POST':
        query = request.form.get('query')
        result = get_channel_data(query, lang)
        if not result: error = content['error']
    return render_template('index.html', content=content, current_lang=lang, result=result, error=error)

@app.route('/araclar/kanal-karsilastir', methods=['GET', 'POST'])
def channel_vs():
    lang = request.args.get('lang', 'tr')
    content = translations.get(lang, translations['tr'])
    result = None
    error = None
    input_data = {}
    if request.method == 'POST':
        q1 = request.form.get('query1')
        q2 = request.form.get('query2')
        input_data = {'query1': q1, 'query2': q2}
        d1 = get_channel_data(q1, lang)
        d2 = get_channel_data(q2, lang)
        if d1 and d2:
            result = {
                'name1': d1['title'], 'name2': d2['title'],
                'subs1': d1['sub_count'], 'subs2': d2['sub_count'],
                'views1': d1['view_count'], 'views2': d2['view_count'],
                'videos1': d1['video_count'], 'videos2': d2['video_count'],
                'grade1': d1['grade'], 'grade2': d2['grade'],
                'daily_subs1': d1['daily_subs'], 'daily_subs2': d2['daily_subs'],
                'earnings1': d1['earnings'], 'earnings2': d2['earnings'],
                'country1': d1['country'], 'country2': d2['country'],
                # --- HAM VERİLER ŞABLONA GÖNDERİLİYOR ---
                'raw_subs1': d1['raw_sub_count'], 'raw_subs2': d2['raw_sub_count'],
                'raw_views1': d1['raw_view_count'], 'raw_views2': d2['raw_view_count'],
                'raw_videos1': d1['raw_video_count'], 'raw_videos2': d2['raw_video_count'],
                'raw_grade1': d1['raw_grade_val'], 'raw_grade2': d2['raw_grade_val'],
                'raw_earnings1': d1['raw_earnings_high'], 'raw_earnings2': d2['raw_earnings_high'],
                'avatar1': d1['avatar'], 'avatar2': d2['avatar']
            }
        else: error = "Kanal verisi alınamadı."
    return render_template('channel_vs.html', content=content, result=result, error=error, input_data=input_data, current_lang=lang)

@app.route('/araclar/video-seo', methods=['GET', 'POST'])
def video_seo():
    lang = request.args.get('lang', 'tr')
    content = translations.get(lang, translations['tr'])
    result = None
    error = None
    if request.method == 'POST':
        q = request.form.get('query')
        vid = extract_video_id(q)
        if vid: result = get_video_data(vid, lang)
        else: error = "Geçersiz Video Linki"
        if not result and vid: error = "Video verisi çekilemedi"
    return render_template('video_seo.html', content=content, result=result, error=error, current_lang=lang)

@app.route('/araclar/ai-baslik', methods=['GET', 'POST'])
def ai_generator():
    ai_result = None
    input_data = {}
    error = None
    MAX_USES = 5
    if 'ai_uses' not in session: session['ai_uses'] = 0
    
    if request.method == 'POST':
        topic = request.form.get('topic')
        style = request.form.get('style')
        captcha = request.form.get('captcha_check')
        expected = session.get('captcha_result')
        
        if session['ai_uses'] >= MAX_USES: error = "Günlük limit doldu."
        elif not captcha or str(captcha) != str(expected): error = "Hatalı işlem sonucu."
        else:
            ai_result = generate_ai_content(topic, style)
            if 'error' not in ai_result: session['ai_uses'] += 1
            else: error = ai_result['error']
        input_data = {'topic': topic, 'style': style}
            
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    session['captcha_result'] = num1 + num2
    uses_left = MAX_USES - session.get('ai_uses', 0)
    return render_template('ai_tool.html', ai_result=ai_result, error=error, input_data=input_data, captcha_question=f"{num1} + {num2} = ?", uses_left=uses_left, max_uses=MAX_USES)

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


