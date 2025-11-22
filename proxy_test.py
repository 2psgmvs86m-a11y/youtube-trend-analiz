import requests

# Senin Proxy Listen
PROXIES = [
    "http://monrtwaa:066g1gqk2esk@216.10.27.159:6837",
    "http://monrtwaa:066g1gqk2esk@198.105.121.200:6462",
    "http://monrtwaa:066g1gqk2esk@198.23.239.134:6540",
    "http://monrtwaa:066g1gqk2esk@142.111.67.146:5611",
    "http://monrtwaa:066g1gqk2esk@142.111.48.253:7030"
]

def test_proxies():
    print("--- PROXY TESTİ BAŞLIYOR ---")
    print("Hedef: YouTube Ana Sayfası\n")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    working_count = 0

    for i, proxy in enumerate(PROXIES):
        proxies_dict = {"http": proxy, "https": proxy}
        try:
            print(f"Proxy {i+1} deneniyor...", end=" ")
            # Timeout 5 saniye: Eğer 5 saniyede bağlanmazsa bozuktur
            response = requests.get("https://www.youtube.com", headers=headers, proxies=proxies_dict, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ ÇALIŞIYOR (Hız: {response.elapsed.total_seconds():.2f}sn)")
                working_count += 1
            else:
                print(f"⚠️ BAĞLANDI AMA HATA: Kod {response.status_code}")
                
        except Exception as e:
            print(f"❌ BOZUK / BAĞLANAMADI")
    
    print(f"\n--- SONUÇ: {working_count} / {len(PROXIES)} Proxy Çalışıyor ---")

if __name__ == "__main__":
    test_proxies()

