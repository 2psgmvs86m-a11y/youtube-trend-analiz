document.addEventListener('DOMContentLoaded', () => {
    const analyzeButton = document.getElementById('analyze-button');
    const channelInput = document.getElementById('channel-url');
    const resultsContainer = document.getElementById('results-container');
    const channelDetails = document.getElementById('channel-details');
    const loadingSpinner = document.getElementById('loading-spinner');

    async function fetchChannelStats() {
        const query = channelInput.value.trim();

        if (!query) {
            alert("Lütfen bir kanal adı veya linki girin.");
            return;
        }

        resultsContainer.style.display = 'block';
        channelDetails.innerHTML = '';
        loadingSpinner.classList.remove('spinner-hidden');
        
        // Girdiyi olduğu gibi Backend'e atıyoruz (Link, isim veya handle)
        // Backend halledecek.
        const apiEndpoint = `/api/channel_stats?query=${encodeURIComponent(query)}`;

        try {
            const response = await fetch(apiEndpoint);
            loadingSpinner.classList.add('spinner-hidden');

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || "Kanal bulunamadı.");
            }

            const data = await response.json();
            
            // HTML Oluşturma (v2 Tasarım)
            channelDetails.innerHTML = `
                <div style="text-align: center; margin-bottom: 30px;">
                    ${data.banner_url ? `<img src="${data.banner_url}" style="width:100%; height: 150px; object-fit: cover; border-radius: 12px; margin-bottom: -40px;">` : ''}
                    <img src="${data.thumbnail}" style="width: 100px; height: 100px; border-radius: 50%; border: 4px solid white; position: relative;">
                    <h2 style="margin: 10px 0;">${data.title}</h2>
                    <p style="color: #666;">${data.customUrl} • ${data.country}</p>
                </div>

                <div class="grid-view" style="grid-template-columns: repeat(4, 1fr); gap: 10px; text-align: center; margin-bottom: 30px;">
                    <div style="background: #fff; padding: 15px; border-radius: 8px; border: 1px solid #eee;">
                        <div style="font-size: 1.2rem; font-weight: bold;">${data.subscribers}</div>
                        <div style="font-size: 0.8rem;">Abone</div>
                    </div>
                    <div style="background: #fff; padding: 15px; border-radius: 8px; border: 1px solid #eee;">
                        <div style="font-size: 1.2rem; font-weight: bold;">${data.views}</div>
                        <div style="font-size: 0.8rem;">İzlenme</div>
                    </div>
                    <div style="background: #fff; padding: 15px; border-radius: 8px; border: 1px solid #eee;">
                        <div style="font-size: 1.2rem; font-weight: bold;">${data.video_count}</div>
                        <div style="font-size: 0.8rem;">Video</div>
                    </div>
                     <div style="background: #fff; padding: 15px; border-radius: 8px; border: 1px solid #eee;">
                        <div style="font-size: 0.9rem; font-weight: bold; color: ${data.is_monetized.includes('AÇIK') ? 'green' : 'red'}">${data.is_monetized}</div>
                        <div style="font-size: 0.8rem;">Para Kazanma</div>
                    </div>
                </div>

                <div class="card">
                    <h3>Kanal SEO Etiketleri</h3>
                    <div class="tag-cloud">
                        ${data.keywords ? data.keywords.split(' ').map(k => `<span class="tag">#${k.replace(/"/g, '')}</span>`).join('') : 'Etiket bulunamadı.'}
                    </div>
                </div>
                
                <div class="card">
                    <h3>Hakkında</h3>
                    <p style="white-space: pre-line;">${data.description}</p>
                </div>
            `;

        } catch (error) {
            loadingSpinner.classList.add('spinner-hidden');
            channelDetails.innerHTML = `<p style="color: red; text-align: center;">${error.message}</p>`;
        }
    }

    analyzeButton.addEventListener('click', fetchChannelStats);
});
