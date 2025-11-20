document.addEventListener('DOMContentLoaded', () => {
    const analyzeButton = document.getElementById('analyze-button');
    const channelUrlInput = document.getElementById('channel-url');
    const resultsContainer = document.getElementById('results-container');
    const channelDetails = document.getElementById('channel-details');
    const loadingSpinner = document.getElementById('loading-spinner');

    function extractChannelId(url) {
        // Kanal ID'sini (UC...) veya kullanıcı adını (@...) URL'den çeker
        let id = null;
        if (url.includes("/channel/")) {
            id = url.split("/channel/")[1].split("/")[0];
        } else if (url.includes("/@")) {
            // Yeni handle formatı
            id = url.split("/@")[1].split("/")[0];
        } else if (url.includes("user/")) {
             id = url.split("/user/")[1].split("/")[0];
        }
        return id;
    }

    async function fetchChannelStats() {
        const url = channelUrlInput.value.trim();
        const channelIdentifier = extractChannelId(url);

        if (!channelIdentifier) {
            channelDetails.innerHTML = '<p style="color: red;">Lütfen geçerli bir kanal URL\'si girin (örn: youtube.com/@kanaladi).</p>';
            resultsContainer.style.display = 'block';
            return;
        }

        resultsContainer.style.display = 'block';
        channelDetails.innerHTML = '';
        loadingSpinner.classList.remove('spinner-hidden');
        
        // Flask API'ye çağrı (ID'yi veya handle'ı gönderiyoruz)
        const apiEndpoint = `/api/channel_stats?id=${channelIdentifier}`;

        try {
            const response = await fetch(apiEndpoint);
            loadingSpinner.classList.add('spinner-hidden');

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `API Hatası: HTTP ${response.status}`);
            }

            const data = await response.json();
            displayChannelDetails(data);

        } catch (error) {
            loadingSpinner.classList.add('spinner-hidden');
            channelDetails.innerHTML = `<p style="color: red;">Analiz Hatası: ${error.message}. Kanal ID'sini kontrol edin veya API kotası dolmuş olabilir.</p>`;
        }
    }

    function displayChannelDetails(data) {
        const detailsHTML = `
            <div style="display: flex; align-items: center; margin-bottom: 20px;">
                <img src="${data.thumbnail}" alt="${data.title}" style="width: 80px; height: 80px; border-radius: 50%; margin-right: 20px;">
                <h2>${data.title}</h2>
            </div>
            <div class="grid-view" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
                <div class="video-card"><strong>Abone Sayısı:</strong> ${data.subscribers}</div>
                <div class="video-card"><strong>Toplam İzlenme:</strong> ${data.views}</div>
                <div class="video-card"><strong>Kayıt Tarihi:</strong> ${data.creation_date}</div>
                <div class="video-card"><strong>Ülke:</strong> ${data.country}</div>
                <div class="video-card"><strong>Para Kazanma:</strong> <span style="font-weight: bold; color: ${data.is_monetized.includes('AÇIK') ? 'green' : 'red'};">${data.is_monetized}</span></div>
            </div>
        `;
        channelDetails.innerHTML = detailsHTML;
    }

    analyzeButton.addEventListener('click', fetchChannelStats);
});

