// --- AYARLAR ---
let currentLang = 'TR';
let isDarkMode = false;

const TRANSLATIONS = {
    'TR': {
        hero_title: 'YouTube Stratejini<br>Veriyle Yönet.',
        hero_desc: 'İçerik üreticileri için gelişmiş rakip analizi.',
        trending_title: 'Gündemdeki Videolar',
        analyze_btn: 'Analiz Et',
        err_fetch: 'Veri çekilemedi.'
    },
    'EN': {
        hero_title: 'Manage Your YouTube<br>Strategy with Data.',
        hero_desc: 'Advanced competitor analysis for creators.',
        trending_title: 'Trending Videos',
        analyze_btn: 'Analyze',
        err_fetch: 'Data could not be fetched.'
    }
};

// --- ORTAK FONKSİYONLAR ---

function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    isDarkMode = !isDarkMode;
    const icon = document.querySelector('.fa-moon');
    if(icon) {
        icon.classList.toggle('fa-moon');
        icon.classList.toggle('fa-sun');
    }
}

function toggleLanguage() {
    currentLang = currentLang === 'TR' ? 'EN' : 'TR';
    // Varsa index textlerini güncelle
    const title = document.getElementById('hero-title-text');
    if(title) {
        title.innerHTML = TRANSLATIONS[currentLang].hero_title;
        document.getElementById('hero-subtitle-text').innerText = TRANSLATIONS[currentLang].hero_desc;
    }
}

// --- ANA SAYFA (INDEX) ARAMA ---
function performSearch() {
    const query = document.getElementById('searchInput').value;
    if(query) {
        // Sorgula sayfasına yönlendir
        window.location.href = `/sorgula?q=${encodeURIComponent(query)}&lang=${currentLang}`;
    }
}

// --- ANALİZ SAYFASI (TRENDLER) ---
async function fetchTrendAnalysis() {
    const region = document.getElementById('regionSelect').value;
    const loader = document.getElementById('loader');
    const ph = document.getElementById('initial-placeholder');
    const results = document.getElementById('results-area');

    if(loader) loader.style.display = 'block';
    if(ph) ph.style.display = 'none';
    if(results) results.style.display = 'none';

    try {
        const res = await fetch(`/api/trending?region=${region}&limit=20`);
        const data = await res.json();
        renderTrendPage(data);
    } catch (e) {
        alert("Hata oluştu: " + e);
        if(ph) ph.style.display = 'block';
    } finally {
        if(loader) loader.style.display = 'none';
    }
}

function renderTrendPage(videos) {
    // Etiketleri topla
    let allTags = [];
    videos.forEach(v => {
        if(v.tags) {
            let tags = [];
            if(Array.isArray(v.tags)) tags = v.tags;
            else try { tags = JSON.parse(v.tags.replace(/'/g, '"')); } catch(e){}
            allTags = allTags.concat(tags);
        }
    });

    // Say
    const counts = {};
    allTags.forEach(t => { counts[t.toLowerCase()] = (counts[t.toLowerCase()] || 0) + 1; });
    const sorted = Object.entries(counts).sort((a,b) => b[1] - a[1]).slice(0, 8);

    // HTML'e bas
    const tagList = document.getElementById('tag-list');
    if(tagList) {
        tagList.innerHTML = '';
        sorted.forEach(([tag, count]) => {
            tagList.innerHTML += `<div class="tag-item">#${tag} (${count})</div>`;
        });
    }

    // İstatistikler
    document.getElementById('total-tags').innerText = allTags.length;
    document.getElementById('results-area').style.display = 'flex';
    
    // Video Listesi
    const vidCont = document.getElementById('video-list-container');
    if(vidCont) {
        vidCont.innerHTML = '';
        videos.slice(0,5).forEach(v => {
            vidCont.innerHTML += `
            <div class="video-row" style="display:flex; gap:10px; margin-bottom:10px;">
                <img src="${v.thumbnail}" style="width:60px; border-radius:4px;">
                <a href="${v.url}" target="_blank" style="text-decoration:none; color:#333;">${v.title}</a>
            </div>`;
        });
        document.getElementById('video-area').style.display = 'block';
    }
}

// --- SORGULA SAYFASI (STATS) ---
async function fetchChannelStats() {
    // URL parametresinden veya inputtan al
    let query = document.getElementById('channelInput') ? document.getElementById('channelInput').value : null;
    
    // Eğer input boşsa ve URL'de q parametresi varsa oradan al (Index'ten yönlendirme)
    if(!query) {
        const urlParams = new URLSearchParams(window.location.search);
        query = urlParams.get('q');
        if(document.getElementById('channelInput')) document.getElementById('channelInput').value = query;
    }

    if (!query) return;

    document.getElementById('loader').style.display = 'block';
    document.getElementById('results').style.display = 'none';

    try {
        const response = await fetch(`/api/channel_stats?query=${encodeURIComponent(query)}&lang=${currentLang}`);
        const data = await response.json();

        if (response.ok) {
            // Basit DOM doldurma
            document.getElementById('p-title').innerText = data.title;
            document.getElementById('p-subs').innerText = data.subscribers;
            document.getElementById('p-views').innerText = data.views;
            document.getElementById('p-img').src = data.thumbnail;
            document.getElementById('p-monetization').innerText = data.is_monetized;
            document.getElementById('p-monetization').style.color = data.monetization_color;
            
            document.getElementById('results').style.display = 'block';
        } else {
            alert(data.error);
        }
    } catch (error) {
        console.error(error);
    } finally {
        document.getElementById('loader').style.display = 'none';
    }
}
