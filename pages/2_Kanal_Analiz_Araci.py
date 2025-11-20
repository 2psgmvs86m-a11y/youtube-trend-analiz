import streamlit as st
from googleapiclient.discovery import build
import os

# --- Özel CSS Enjeksiyonu (Tasarım Yenileme) ---
st.markdown("""
<style>
/* Arka Plan ve Ana Renkler */
.stApp {
    background-color: #f0f2f6; /* Açık gri tonu */
    color: #1e1e1e; /* Koyu metin */
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
/* Başlık Rengi */
h1 {
    color: #e50000; /* YouTube kırmızısı */
}
/* Buton Görünümü */
div.stButton > button:first-child {
    background-color: #e50000;
    color: white;
    border-radius: 8px;
    border: 0px;
    padding: 10px 24px;
    font-size: 16px;
    font-weight: bold;
    box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.2);
}
/* Buton hover efekti */
div.stButton > button:first-child:hover {
    background-color: #ff3333;
}
</style>
""", unsafe_allow_html=True)
# -----------------------------------------------

# --- API Anahtari Cekiliyor ---
API_KEY = os.environ.get("YOUTUBE_API_KEY")

if not API_KEY:
    st.error("HATA: API Anahtarı mevcut değil.")
    st.stop()

youtube = build('youtube', 'v3', developerKey=API_KEY)

# --- Fonksiyonlar ---
def get_channel_stats(channel_id):
    """Kanal ID'si ile abone ve izlenme istatistiklerini çeker."""
    request = youtube.channels().list(
        part="snippet,statistics,status",
        id=channel_id
    )
    response = request.execute()
    return response.get('items', [{}])[0]

def get_channel_id_from_url(url):
    """YouTube URL'sinden olası Channel ID'yi veya Kullanıcı Adını ayıklar."""
    from urllib.parse import urlparse, parse_qs
    
    if "youtube.com/channel/" in url:
        return url.split("/channel/")[1].split("/")[0], 'id'
    elif "youtube.com/user/" in url:
        return url.split("/user/")[1].split("/")[0], 'user'
    elif "youtube.com/@" in url:
        # Yeni handle (kullanıcı adı) formatı
        return url.split("/@")[1].split("/")[0], 'handle'
    return None, None

def get_channel_id_by_name(name, search_type):
    """Kullanıcı adı veya handle ile ID'yi arar."""
    
    # API'de handle ve kullanıcı adı için doğrudan metodlar karmaşık, arama yapmayı deniyoruz
    search_response = youtube.search().list(
        q=name,
        type='channel',
        part='snippet',
        maxResults=1
    ).execute()
    
    for item in search_response.get('items', []):
        if item['snippet']['channelId']:
            return item['snippet']['channelId']
    return None

# --- Arayüz ---
st.title("🔗 YouTube Kanal Analiz Aracı")
st.markdown("---")

channel_url = st.text_input(
    "Analiz etmek istediğiniz YouTube Kanal Linkini girin:",
    placeholder="Örn: https://www.youtube.com/@TechCrunch"
)

if st.button("Analiz Et"):
    if not channel_url:
        st.warning("Lütfen geçerli bir kanal linki girin.")
    else:
        with st.spinner('Kanal verileri çekiliyor...'):
            channel_data = None
            
            # URL'den ID veya isim cikarimi
            identifier, id_type = get_channel_id_from_url(channel_url)
            
            if identifier:
                channel_id = None
                if id_type == 'id':
                    channel_id = identifier
                else: # user name or handle
                    channel_id = get_channel_id_by_name(identifier, id_type)
                
                if channel_id:
                    channel_data = get_channel_stats(channel_id)

            if channel_data:
                snippet = channel_data.get('snippet', {})
                stats = channel_data.get('statistics', {})
                status = channel_data.get('status', {})

                st.header(f"📊 {snippet.get('title', 'Bilinmeyen Kanal')}")
                st.image(snippet.get('thumbnails', {}).get('high', {}).get('url', ''))
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Toplam Abone", f"{int(stats.get('subscriberCount', 0)):,}", 
                              help="Kanalın anlık abone sayısıdır.")
                
                with col2:
                    st.metric("Toplam İzlenme", f"{int(stats.get('viewCount', 0)):,}",
                              help="Kanalın toplam izlenme sayısıdır.")
                
                with col3:
                    # Monetizasyon Durumu Tahmini (YPP Kriterlerine Dayalı)
                    is_monetized = "Bilinmiyor"
                    sub_count = int(stats.get('subscriberCount', 0))
                    view_count = int(stats.get('viewCount', 0))

                    if sub_count >= 1000 and view_count > 40000:
                         is_monetized = "Yüksek İhtimalle AÇIK"
                    else:
                         is_monetized = "Düşük İhtimal"
                    
                    st.metric("Para Kazanma Durumu", is_monetized, 
                              help="YPP kriterlerine (1K Abone, 4K saat izlenme) göre tahmindir.")
                
                st.subheader("Kanal Detayları")
                st.info(f"Açıklama: {snippet.get('description', 'Açıklama yok.')}")

            else:
                st.error("Kanal verisi çekilemedi veya link geçerli değil. Lütfen URL'yi kontrol edin.")

