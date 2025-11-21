document.addEventListener('DOMContentLoaded', () => {
    const analyzeButton = document.getElementById('analyze-button');
    const channelInput = document.getElementById('channel-url');
    const resultsContainer = document.getElementById('results-container');
    const channelDetails = document.getElementById('channel-details');
    const loadingSpinner = document.getElementById('loading-spinner');

    // --- YENİ: URL PARAMETRESİNİ KONTROL ET ---
    // Eğer kullanıcı ana sayfadan geldiyse (?q=MrBeast gibi), otomatik başlat
    const urlParams = new URLSearchParams(window.location.search);
    const queryFromUrl = urlParams.get('q');

    if (queryFromUrl) {
        channelInput.value = queryFromUrl; // Kutucuğa yaz
        fetchChannelStats(queryFromUrl);   // Aramayı başlat
    }

    async function fetchChannelStats(manualQuery = null) {
        // Eğer manuelQuery (URL'den gelen) varsa onu kullan, yoksa input'tan al
        const query = manualQuery || channelInput.value.trim();

        if (!query) {
            alert("Lütfen bir kanal adı veya linki girin.");
            return;
        }

        resultsContainer.style.display = 'block';
        channelDetails.innerHTML = '';
        loadingSpinner.classList.remove('spinner-hidden');
        
        const apiEndpoint = `/api/channel_stats?query=${encodeURIComponent(query)}`;

        try {
            const response = await fetch(apiEndpoint);
            loadingSpinner.classList.add('spinner-hidden');

            if (!response.ok) {
                throw new Error("Kanal bulunamadı.");
            }

            const data = await response.json();
            
            // Anahtar kelimeleri düzelt
            let keywordHTML = '';
            if (data.keywords) {
                keywordHTML = data.keywords.replace(/"/g, '').split(' ')
                    .filter(k => k.length > 1)
                    .map(k => `<span class="tag">#${k}</span>`).join('');
            } else {
                keywordHTML = '<span style="color:#999; font-size:0.8rem;">Etiket yok</span>';
            }

            channelDetails.innerHTML = `
                <div style="text-align: center; margin-bottom: 30px;">
                    ${data.banner_url ? `<img src="${data.banner_url}" style="width:100%; height: 150px; object-fit: cover; border-radius: 12px; margin-bottom: -50px; position: relative; z-index: 1;">` : ''}
                    <img src="${data.thumbnail}" style="width: 100px; height: 100px; border-radius: 50%; border: 4px solid white; position: relative; z-index: 2; background: white; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                    <h2 style="margin: 15px 0 5px 0;">${data.title}</h2>
                    <p style="color: #666;">${data.customUrl} • ${data.country}</p>
                </div>

                <div class="grid-view" style="grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; text-align: center; margin-bottom: 30px;">
                    <div style="background: #fff; padding: 15px; border-radius: 12px; border: 1px solid #eee;">
                        <div style="font-weight: 800; font-size: 1.1rem;">${data.subscribers}</div>
                        <div style="font-size: 0.8rem; color: #666;">Abone</div>
                    </div>
                    <div style="background: #fff; padding: 15px; border-radius: 12px; border: 1px solid #eee;">
                        <div style="font-weight: 800; font-size: 1.1rem;">${data.views}</div>
                        <div style="font-size: 0.8rem; color: #666;">İzlenme</div>
                    </div>
                    <div style="background: #fff; padding: 15px; border-radius: 12px; border: 1px solid #eee;">
                        <div style="font-weight: 800; font-size: 1.1rem;">${data.video_count}</div>
                        <div style="font-size: 0.8rem; color: #666;">Video</div>
                    </div>
                </div>

                <div class="glass-card" style="padding: 20px; margin-bottom: 20px;">
                    <h3 style="margin-top:0; font-size: 1rem;">Kanal SEO Etiketleri</h3>
                    <div class="tag-cloud">${keywordHTML}</div>
                </div>

                <div class="glass-card" style="padding: 20px;">
                    <h3 style="margin-top:0; font-size: 1rem;">Hakkında</h3>
                    <p style="white-space: pre-line; font-size: 0.9rem; color: #444; line-height: 1.6;">${data.description || "Açıklama yok."}</p>
                </div>
            `;

        } catch (error) {
            loadingSpinner.classList.add('spinner-hidden');
            channelDetails.innerHTML = `<p style="color: red; text-align: center; margin-top: 20px;">❌ ${error.message}</p>`;
        }
    }

    analyzeButton.addEventListener('click', () => fetchChannelStats());
});
