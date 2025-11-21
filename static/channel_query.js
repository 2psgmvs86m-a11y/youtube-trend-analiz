document.addEventListener('DOMContentLoaded', () => {
    const analyzeButton = document.getElementById('analyze-button');
    const channelInput = document.getElementById('channel-url');
    const resultsContainer = document.getElementById('results-container');
    const channelDetails = document.getElementById('channel-details');
    const loadingSpinner = document.getElementById('loading-spinner');

    // URL'den otomatik arama
    const urlParams = new URLSearchParams(window.location.search);
    const queryFromUrl = urlParams.get('q');
    if (queryFromUrl) {
        channelInput.value = queryFromUrl;
        fetchChannelStats(queryFromUrl);
    }

    async function fetchChannelStats(manualQuery = null) {
        const query = manualQuery || channelInput.value.trim();
        if (!query) { alert("Lütfen bir kanal adı girin."); return; }

        resultsContainer.style.display = 'block';
        channelDetails.innerHTML = '';
        loadingSpinner.style.display = 'block';
        
        try {
            const response = await fetch(`/api/channel_stats?query=${encodeURIComponent(query)}`);
            loadingSpinner.style.display = 'none';

            if (!response.ok) throw new Error("Kanal bulunamadı.");
            const data = await response.json();
            
            // HTML OLUŞTURUCU
            // 1. Etiketler
            let keywordHTML = data.keywords ? data.keywords.replace(/"/g, '').split(' ').filter(k=>k.length>1).map(k => `<span class="tag">#${k}</span>`).join('') : '<span style="color:#999">Etiket yok</span>';

            // 2. Son Videolar
            let videosHTML = '';
            if(data.recent_videos && data.recent_videos.length > 0){
                videosHTML = `<div class="grid-view" style="grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap:10px; margin-top:10px;">`;
                data.recent_videos.forEach(vid => {
                    videosHTML += `
                    <a href="https://www.youtube.com/watch?v=${vid.videoId}" target="_blank" style="text-decoration:none; color:inherit;">
                        <div class="glass-card" style="border:none; box-shadow:none; background:rgba(0,0,0,0.03);">
                            <img src="${vid.thumbnail}" style="width:100%; border-radius:8px;">
                            <div style="font-size:0.75rem; font-weight:600; margin-top:5px; padding:5px; line-height:1.2;">${vid.title}</div>
                        </div>
                    </a>`;
                });
                videosHTML += `</div>`;
            }

            channelDetails.innerHTML = `
                <div style="text-align: center; margin-bottom: 30px;">
                    ${data.banner_url ? `<img src="${data.banner_url}" style="width:100%; height: 130px; object-fit: cover; border-radius: 12px; margin-bottom: -45px; opacity:0.9;">` : ''}
                    <img src="${data.thumbnail}" style="width: 90px; height: 90px; border-radius: 50%; border: 4px solid white; position: relative; z-index: 2; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
                    <h2 style="margin: 10px 0 5px 0;">${data.title}</h2>
                    <p style="color: var(--text-sec); font-size: 0.9rem;">${data.customUrl} • ${data.country}</p>
                </div>

                <div class="grid-view" style="grid-template-columns: repeat(3, 1fr); gap: 10px; text-align: center; margin-bottom: 20px;">
                    <div class="glass-card" style="padding: 15px;">
                        <div style="font-size: 1.2rem; font-weight: 800;">${data.subscribers}</div>
                        <div style="font-size: 0.8rem; color: var(--text-sec);">Abone</div>
                    </div>
                    <div class="glass-card" style="padding: 15px;">
                        <div style="font-size: 1.2rem; font-weight: 800;">${data.views}</div>
                        <div style="font-size: 0.8rem; color: var(--text-sec);">İzlenme</div>
                    </div>
                    <div class="glass-card" style="padding: 15px;">
                        <div style="font-size: 1.2rem; font-weight: 800;">${data.video_count}</div>
                        <div style="font-size: 0.8rem; color: var(--text-sec);">Video</div>
                    </div>
                </div>

                <div class="grid-view" style="grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; margin-bottom: 20px;">
                    <div class="glass-card" style="padding: 15px; border-left: 5px solid ${data.monetization_color};">
                        <h4 style="margin:0 0 5px 0; color:${data.monetization_color};">💰 Para Kazanma</h4>
                        <div style="font-weight:700;">${data.is_monetized}</div>
                        <div style="font-size: 0.8rem; margin-top:5px;">Tahmini Toplam Gelir:</div>
                        <div style="font-size: 1.1rem; font-weight: 800; color: var(--text-main);">${data.est_earnings_min} - ${data.est_earnings_max}</div>
                    </div>
                    <div class="glass-card" style="padding: 15px; border-left: 5px solid #007bff;">
                        <h4 style="margin:0 0 5px 0; color:#007bff;">📊 Kalite Skoru: ${data.score}</h4>
                        <div style="font-size: 0.9rem;">Ortalama İzlenme: <strong>${data.avg_views}</strong></div>
                        <div style="font-size: 0.9rem;">Son Yükleme: <strong>${data.last_upload_date}</strong></div>
                    </div>
                </div>

                <div class="glass-card" style="padding: 20px; margin-bottom: 20px;">
                    <h3 style="margin-top:0; font-size: 1rem; border-bottom:1px solid var(--glass-border); padding-bottom:10px;">🎬 Son Videolar</h3>
                    ${videosHTML}
                </div>

                <div class="glass-card" style="padding: 20px; margin-bottom: 20px;">
                    <h3 style="margin-top:0; font-size: 1rem;">🏷️ Kanal Etiketleri</h3>
                    <div style="margin-top:10px;">${keywordHTML}</div>
                </div>

                <div class="glass-card" style="padding: 20px;">
                    <h3 style="margin-top:0; font-size: 1rem;">ℹ️ Hakkında</h3>
                    <div style="max-height: 150px; overflow-y: auto; font-size: 0.9rem; color: var(--text-sec); line-height: 1.6; white-space: pre-line;">${data.description || "Açıklama yok."}</div>
                </div>
            `;

        } catch (error) {
            loadingSpinner.style.display = 'none';
            channelDetails.innerHTML = `<p style="color: red; text-align: center;">❌ ${error.message}</p>`;
        }
    }

    analyzeButton.addEventListener('click', () => fetchChannelStats());
});
