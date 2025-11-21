document.addEventListener('DOMContentLoaded', () => {
    
    // --- DİL AYARLARI ---
    const translations = {
        tr: {
            title: 'YouTube Stratejini <br>Veriyle Yönet.',
            desc: 'İçerik üreticileri için en gelişmiş rakip analizi, etiket bulucu ve trend takip aracı.',
            placeholder: 'Kanal linki veya ismi girin...',
            trendHeader: 'Gündemdeki Videolar'
        },
        en: {
            title: 'Master YouTube <br>With Data.',
            desc: 'Advanced competitor analysis, tag finder, and trend tracking tool for creators.',
            placeholder: 'Enter channel link or name...',
            trendHeader: 'Trending Now'
        }
    };

    const langSelector = document.getElementById('language-selector');
    
    langSelector.addEventListener('change', (e) => {
        const lang = e.target.value;
        const t = translations[lang];
        
        document.getElementById('hero-title').innerHTML = t.title;
        document.getElementById('hero-desc').textContent = t.desc;
        document.getElementById('main-search').placeholder = t.placeholder;
        document.getElementById('trend-header').textContent = t.trendHeader;
        
        fetchTrends(lang === 'tr' ? 'TR' : 'US');
    });

    // --- DARK MODE ---
    const themeBtn = document.getElementById('theme-toggle');
    const icon = themeBtn.querySelector('i');
    
    // Kullanıcının tercihini hatırla (LocalStorage)
    if(localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark-mode');
        icon.classList.replace('fa-moon', 'fa-sun');
    }

    themeBtn.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        
        if (isDark) {
            icon.classList.replace('fa-moon', 'fa-sun');
        } else {
            icon.classList.replace('fa-sun', 'fa-moon');
        }
    });

    // --- ARAMA FONKSİYONU ---
    const searchBtn = document.getElementById('search-btn');
    const searchInput = document.getElementById('main-search');

    function goSearch() {
        const q = searchInput.value.trim();
        if(q) window.location.href = `/sorgula?q=${encodeURIComponent(q)}`; // Kullanıcıyı yönlendir
    }

    searchBtn.addEventListener('click', goSearch);
    searchInput.addEventListener('keypress', (e) => { if(e.key === 'Enter') goSearch(); });

    // --- TRENDLERİ ÇEK ---
    function fetchTrends(region = 'TR') {
        const list = document.getElementById('video-list');
        list.innerHTML = '<p style="opacity:0.6; padding-left:20px;">Yükleniyor...</p>';

        fetch(`/api/trending?region=${region}&limit=4`)
            .then(res => res.json())
            .then(data => {
                list.innerHTML = '';
                data.forEach(video => {
                    list.innerHTML += `
                        <div class="glass-card">
                            <a href="${video.url}" target="_blank">
                                <img src="${video.thumbnail}" class="card-thumb">
                            </a>
                            <div class="card-content">
                                <div class="card-title">${video.title}</div>
                                <div class="card-meta">
                                    <span>${video.channel}</span>
                                    <span class="badge">${new Intl.NumberFormat('tr-TR').format(video.views)}</span>
                                </div>
                            </div>
                        </div>
                    `;
                });
            });
    }

    fetchTrends('TR');
});
