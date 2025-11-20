import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
import os
import collections

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

# --- Yeni Eklenen Bolge Kodlari ve Haritalama ---
REGION_MAP = {
    "Türkiye (TR)": "TR",
    "Global (US)": "US",
    "Almanya (DE)": "DE",
    "Fransa (FR)": "FR",
    "Japonya (JP)": "JP",
    "Güney Kore (KR)": "KR"
}


def get_trending_videos(region_code, max_results=30):
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

st.title("🔥 Anlık YouTube Trendleri Analiz Motoru")
st.markdown("---")

# Yan Menü (Sidebar) ile Bolge Secimi
st.sidebar.header("Ayarlar")
selected_region_name = st.sidebar.selectbox(
    "1. Bölge Seçimi:",
    list(REGION_MAP.keys())
)
selected_region_code = REGION_MAP[selected_region_name]

# Veri Cekme Butonu
if st.button(f'{selected_region_name} Trendlerini Yenile'):
    st.spinner(f"{selected_region_name} için trendler çekiliyor, lütfen bekleyin...")
    
    df_videos = get_trending_videos(region_code=selected_region_code, max_results=30)
    
    if not df_videos.empty:
        # Görüntülenme sayılarını okunabilir hale getir
        df_videos['Goruntulenme'] = df_videos['Goruntulenme'].apply(lambda x: f"{x:,}")

        st.header(f"{selected_region_name} - En Çok İzlenen Videolar")
        st.dataframe(df_videos[['Baslik', 'Kanal', 'Goruntulenme', 'URL']], hide_index=True)
        
        # ----------------------------------------------------------------------------------
        # Yeni: Grafiksel Kelime Analizi
        
        st.header("🔍 Popüler Anahtar Kelimeler")
        
        # Basit Kelime Analizi
        all_titles = " ".join(df_videos['Baslik']).lower()
        # Kelimeleri ayır ve 4 harften uzun ve sadece harf iceren kelimeleri filtrele
        words = [word for word in all_titles.split() if len(word) > 4 and word.isalpha()]
        word_counts = collections.Counter(words).most_common(10)

        # Bar Grafik Hazırlığı
        df_keywords = pd.DataFrame(word_counts, columns=['Anahtar Kelime', 'Tekrar Sayısı'])
        
        # Bar Grafik Ekleme
        st.subheader("En Çok Tekrar Eden 10 Anahtar Kelime")
        st.bar_chart(df_keywords.set_index('Anahtar Kelime'))
        
        # Tabloyu da Istege Bagli Gosterelim
        with st.expander("Tüm Verileri Tabloda Gör"):
             st.dataframe(df_keywords, hide_index=True)
        
        # ----------------------------------------------------------------------------------
    else:
        st.warning(f"{selected_region_name} için trend verisi çekilemedi. API Anahtarını kontrol edin veya kotanız dolmuş olabilir.")

