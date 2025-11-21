import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# API Key Render Environment'tan gelir
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')

translations = {
    'tr': {
        'title': 'YouTube Kanal Analizi',
        'placeholder': 'Kanal Adı veya ID girin...',
        'search_btn': 'Analiz Et',
        'subs': 'Abone',
        'views': 'Görüntülenme',
        'videos': 'Video Sayısı',
        'latest_videos': 'Son Yüklenen Videolar',
        'financial_title': 'Finansal Tahminler',
        'monetization': 'Para Kazanma Durumu',
        'est_earnings': 'Tahmini Toplam Kazanç',
        'active': 'Açık Olabilir (Uygun)',
        'passive': 'Kapalı (Yetersiz Abone)',
        'note': '*Bu veriler tahmini olup CPM oranlarına göre değişebilir.',
        'error': 'Kanal bulunamadı veya API hatası.',
        'desc': 'Kanalın performansını, gelir tahminini ve içeriklerini görün.'
    },
    'en': {
        'title': 'YouTube Channel Analysis',
        'placeholder': 'Enter Channel Name or ID...',
        'search_btn': 'Analyze',
        'subs': 'Subscribers',
        'views': 'Total Views',
        'videos': 'Total Videos',
        'latest_videos': 'Latest Uploads',
        'financial_title': 'Financial Estimates',
        'monetization': 'Monetization Status',
        'est_earnings': 'Est. Total Earnings',
        'active': 'Likely Active (Eligible)',
        'passive': 'Inactive (Not Eligible)',
        'note': '*These figures are estimates based on avg CPM rates.',
        'error': 'Channel not found or API error.',
        'desc': 'View channel performance, revenue estimates and content.'
    },
    'de': {
        'title': 'YouTube-Kanalanalyse',
        'placeholder': 'Kanalname oder ID eingeben...',
        'search_btn': 'Analysieren',
        'subs': 'Abonnenten',
        'views': 'Gesamtansichten',
        'videos': 'Videos',
        'latest_videos': 'Neueste Videos',
        'financial_title': 'Finanzielle Schätzungen',
        'monetization': 'Monetarisierungsstatus',
        'est_earnings': 'Geschätzter Gesamtverdienst',
        'active': 'Wahrscheinlich Aktiv',
        'passive': 'Inaktiv',
        'note': '*Diese Zahlen sind Schätzungen.',
        'error': 'Kanal nicht gefunden oder API-Fehler.',
        'desc': 'Sehen Sie Kanalleistung und Umsatzschätzungen.'
    }
}

def format_currency(amount):
    return "${:,.2f}".format(amount)

def get_channel_data(query):
    if not YOUTUBE_API_KEY:
        raise Exception("API Key Eksik! Render ayarlarını kontrol et.")

    # 1. Kanal ID Bul
    search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=channel&key={YOUTUBE_API_KEY}"
    search_res = requests.get(search_url).json()

    if not search_res.get('items'):
        return None

    channel_id = search_res['items'][0]['id']['channelId']

    # 2. İstatistikler
    stats_url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics,snippet,contentDetails&id={channel_id}&key={YOUTUBE_API_KEY}"
    stats_res = requests.get(stats_url).json()
    
    if not stats_res.get('items'):
        return None
        
    channel_info = stats_res['items'][0]
    stats = channel_info['statistics']

    # --- HESAPLAMA MANTIĞI (SocialBlade Benzeri) ---
    view_count = int(stats.get('viewCount', 0))
    sub_count = int(stats.get('subscriberCount', 0))
    
    # 1. Para Kazanma Kontrolü (Basit Kural: 1000 Abone)
    monetization_status = sub_count >= 1000

    # 2. Gelir Tahmini (CPM: $0.25 - $4.00 arası)
    # Toplam izlenmeyi 1000'e bölüp CPM ile çarpıyoruz
    min_earnings = (view_count / 1000) * 0.25
    max_earnings = (view_count / 1000) * 4.00

    earnings_str = f"{format_currency(min_earnings)} - {format_currency(max_earnings)}"

    # 3. Son Videolar
    videos = []
    try:
        uploads_id = channel_info['contentDetails']['relatedPlaylists']['uploads']
        videos_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={uploads_id}&maxResults=3&key={YOUTUBE_API_KEY}"
        videos_res = requests.get(videos_url).json()

        for item in videos_res.get('items', []):
            videos.append({
                'title': item['snippet']['title'],
                'thumb': item['snippet']['thumbnails']['medium']['url'],
                'id': item['snippet']['resourceId']['videoId'],
                'published': item['snippet']['publishedAt'][:10]
            })
    except:
        pass

    return {
        'title': channel_info['snippet']['title'],
        'desc': channel_info['snippet']['description'],
        'avatar': channel_info['snippet']['thumbnails']['medium']['url'],
        'stats': stats,
        'monetized': monetization_status,
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
                if not result:
                    error = content['error']
            except Exception as e:
                error = f"Hata: {e}"

    return render_template('index.html', content=content, current_lang=lang, result=result, error=error)

if __name__ == '__main__':
    app.run(debug=True)

