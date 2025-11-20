document.addEventListener('DOMContentLoaded', () => {
    const fetchButton = document.getElementById('fetch-button');
    const regionSelect = document.getElementById('region-select');
    const videoList = document.getElementById('video-list');
    const loadingSpinner = document.getElementById('loading-spinner');

    // Verileri API'dan çeken ana fonksiyon
    async function fetchTrendingData() {
        videoList.innerHTML = '';
        loadingSpinner.classList.remove('spinner-hidden');

        const selectedRegion = regionSelect.value;
        const apiEndpoint = `/api/trending?region=${selectedRegion}`; // Flask API'ye çağrı

        try {
            const response = await fetch(apiEndpoint);
            
            if (!response.ok) {
                throw new Error(`API Hatası: HTTP durum kodu ${response.status}`);
            }

            const data = await response.json();

            loadingSpinner.classList.add('spinner-hidden');
            displayVideos(data);
        } catch (error) {
            loadingSpinner.classList.add('spinner-hidden');
            videoList.innerHTML = `<p style="color: red;">Veri çekilemedi: ${error.message}. API Anahtarınızı ve kotanızı kontrol edin.</p>`;
        }
    }

    // Videoları HTML'e yerleştiren fonksiyon
    function displayVideos(videos) {
        if (videos.length === 0) {
            videoList.innerHTML = '<p>Bu bölge için trend verisi bulunamadı.</p>';
            return;
        }

        videos.forEach(video => {
            const card = document.createElement('div');
            card.className = 'video-card';
            
            // İzlenme sayısını formatlama (Örn: 1,234,567)
            const formattedViews = new Intl.NumberFormat('tr-TR').format(video.views);

            card.innerHTML = `
                <h3 class="video-title">${video.title}</h3>
                <p><strong>Kanal:</strong> ${video.channel}</p>
                <p class="video-stats">👁️ İzlenme: ${formattedViews}</p>
                <a href="${video.url}" target="_blank" style="color: #007bff; text-decoration: none; font-weight: 600;">Videoyu İzle</a>
            `;
            videoList.appendChild(card);
        });
    }

    // Olay Dinleyicileri
    fetchButton.addEventListener('click', fetchTrendingData);

    // Sayfa yüklendiğinde varsayılan trendleri çek (Türkiye)
    fetchTrendingData();
});

