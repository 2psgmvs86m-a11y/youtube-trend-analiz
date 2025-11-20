import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
import os

# --- GUVENLIK: API Anahtarini Ortam Degiskenlerinden Cek ---
# Bu, kodun hackerlar tarafindan gorulmesini engeller.
API_KEY = os.environ.get("YOUTUBE_API_KEY")

if not API_KEY:
    st.error("HATA: YouTube API anahtarı Ortam Değişkenlerinde (Render'da) ayarlanmamış.")
    st.stop()

# API Servisini Baslatma
try:
    youtube = build('youtube', 'v3', developerKey=API_KEY)
except Exception as e:
    st.error(f"API Bağlantı Hatası: {e}")
    st.stop()

def get_trending_videos(region_code="TR", max_results=20):
    """Belirtilen bolgedeki trend videoları çeker."""
    request = youtube.videos().list(
        part="snippet,statistics",
        chart="mostPopular",
        regionCode=region_code,
        maxResults=max_results
    )
    response = request.execute()
    
    video_data = []
    for item in response.get("items", []):
        video_data.append({
            "Baslik": item['snippet']['title'],
            "Kanal": item['snippet']['channelTitle'],
            "Goruntulenme": int(item['statistics'].get('viewCount', 0)),
            "URL": f"https://www.youtube.com/watch?v={item['id']}"
        })
    return pd.DataFrame(video_data)

st.set_page_config(layout="wide", page_title="YouTube Trend Analizi")

st.title("🔥 Anlık YouTube Türkiye Trendleri Analizi")
st.markdown("---")

# Veri Cekme Butonu
if st.button('Trend Verilerini Yenile'):
    st.spinner("Trendler çekiliyor, lütfen bekleyin...")
    
    df_videos = get_trending_videos(region_code="TR", max_results=30)
    
    if not df_videos.empty:
        # Görüntülenme sayılarını okunabilir hale getir
        df_videos['Goruntulenme'] = df_videos['Goruntulenme'].apply(lambda x: f"{x:,}")

        st.header("En Çok İzlenen Videolar")
        st.dataframe(df_videos[['Baslik', 'Kanal', 'Goruntulenme', 'URL']], hide_index=True)
        
        # Basit Kelime Analizi
        all_titles = " ".join(df_videos['Baslik']).lower()
        import collections
        words = [word for word in all_titles.split() if len(word) > 4 and word.isalpha()]
        word_counts = collections.Counter(words).most_common(10)

        st.header("🔍 Popüler Anahtar Kelimeler")
        df_keywords = pd.DataFrame(word_counts, columns=['Anahtar Kelime', 'Tekrar Sayısı'])
        st.dataframe(df_keywords, hide_index=True)
    else:
        st.warning("Trend verisi çekilemedi. API Anahtarını kontrol edin veya kotanız dolmuş olabilir.")

