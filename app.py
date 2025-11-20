import streamlit as st

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

# Sayfa Ayarları (Global Tema ve Layout)
st.set_page_config(
    page_title="Ana Sayfa | YouTube Analiz Motoru",
    layout="wide",
    initial_sidebar_state="expanded" 
)

st.title("🌟 YouTube Trend ve Kanal Analiz Motoruna Hoş Geldiniz!")
st.subheader("İçerik Stratejinizi Verilerle Güçlendirin.")

st.markdown("---")

# Sitenin Amacı
st.markdown("""
Bu platform, YouTube dünyasındaki en güncel verileri ve trendleri tek bir yerde toplayarak, içerik üreticileri, pazarlamacılar ve meraklılar için **anlık analiz imkanı** sunar.
""")

col1, col2 = st.columns(2)

with col1:
    st.header("📊 Trendleri Keşfedin")
    st.markdown("""
    Sol menüdeki **'Trend Analiz Paneli'** aracılığıyla Türkiye ve dünya genelindeki en popüler videoları anlık olarak görüntüleyebilirsiniz.
    En çok tekrar eden anahtar kelimeleri grafiklerle inceleyerek hangi konuların zirvede olduğunu hızla anlayın.
    """)
    st.info("Bu araç, içerik fikri bulmak ve pazar araştırması yapmak için idealdir.")

with col2:
    st.header("🔗 Kanal Analizi Yapın")
    st.markdown("""
    **'Kanal Analiz Aracı'** ile rakiplerinizin veya potansiyel iş ortaklarınızın kanal linkini girerek anlık istatistiklerine ulaşın:
    * **Abone Sayısı** ve **Toplam İzlenme**
    * **Para Kazanma Durumu** tahmini
    * Kanalın genel durumu ve büyüme potansiyeli.
    """)
    st.info("Bu araç, rakip analizi ve performans takibi için vazgeçilmezdir.")

st.markdown("---")

# Görsel İpucu ve Yönlendirme
st.warning("👉 Tüm araçlarımıza erişmek için sol taraftaki menüyü (Sidebar) kullanınız.")
