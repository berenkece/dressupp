# DressUpp — Geliştirme Planı (Sıra Sıra)

Her adım bir öncekinin üstüne biniyor. Kural: **bir adım "bitti" olmadan sonrakine geçme.** Her adımda ne yapacağın, hangi dosyaya dokunacağın, "bitti" kriteri ve ne öğreneceğin yazılı.

Genel akış üç bloğa ayrılıyor:
- **A. Çalışan prototip** (Adım 0–6) → elinde gösterilebilir bir demo olur
- **B. Kendi eğittiğin modeller** (Adım 7–9) → işin data science kalbi
- **C. İleri seviye + yayın** (Adım 10–12) → trend, internet parçası, deploy

---

## BLOK A — Çalışan Prototip

### Adım 0 — Ortam kurulumu
- **Yap:** venv oluştur, `pip install -r requirements.txt`, `streamlit run app.py` çalıştığını gör (boş sayfa olsa da).
- **Dosya:** —
- **Bitti:** Streamlit tarayıcıda açılıyor, hata yok.
- **Öğrenirsin:** Proje ortamını izole kurma alışkanlığı.

### Adım 1 — Arka plan kaldırma
- **Yap:** `rembg` ile foto → şeffaf PNG. Sonuca bounding-box kırpma ekle.
- **Dosya:** `src/segmentation.py`
- **Bitti:** Bir kıyafet fotoğrafı verince arka planı temiz kalkmış PNG dönüyor.
- **Öğrenirsin:** Hazır CV modelini pipeline'a bağlama, RGBA/maske mantığı.

### Adım 2 — Baskın renk çıkarımı
- **Yap:** Şeffaf pikselleri ele, `KMeans` ile ~3 baskın renk, hex + HSV döndür.
- **Dosya:** `src/color.py`
- **Bitti:** Bir PNG verince `["#1a2b3c", ...]` gibi renk listesi dönüyor.
- **Öğrenirsin:** k-means, renk uzayları (RGB↔HSV) — uyum motorunun temeli.

### Adım 3 — Streamlit prototipini birleştir
- **Yap:** Yükle → arka plan kaldır → renkleri göster akışını tek ekranda bağla.
- **Dosya:** `app.py`
- **Bitti:** Tarayıcıdan foto yükleyip sonucu ve renkleri görüyorsun.
- **Öğrenirsin:** Streamlit ile modülleri uçtan uca bağlama.

### Adım 4 — Veri modeli + gardırop kalıcılığı
- **Yap:** `ClothingItem` / `Outfit` tanımla; parçaları basit bir yerde sakla (JSON ya da SQLite).
- **Dosya:** `src/schema.py`, küçük bir `storage` katmanı
- **Bitti:** Yüklenen parça kaydediliyor, uygulama kapanıp açılınca gardırop duruyor.
- **Öğrenirsin:** Veri modelleme, kalıcılık (persistence).

### Adım 5 — Manuel etiketleme
- **Yap:** Yükleme sırasında kategori / stil / mevsim için dropdown. (Otomatik etiketleme Adım 7'de gelecek; şimdilik elle.)
- **Dosya:** `app.py`, `src/schema.py`
- **Bitti:** Her parçanın kategori + etiketleri var, gardırop ızgarasında filtreleyebiliyorsun.
- **Öğrenirsin:** Ürün akışı; modelsiz de değer üretmek (v1 mantığı).

### Adım 6 — Kural tabanlı uyum motoru
- **Yap:** Renk çemberi uyumu (tamamlayıcı/analog/nötr) + kategori/mevsim kurallarıyla 0–100 skor. Bir parça seçince "bunlar yakışır" listesi.
- **Dosya:** `src/compatibility.py`
- **Bitti:** Bir üst seçince gardıroptan uyumlu altlar skorlanıp sıralanıyor. Seçim kullanıcıda.
- **Öğrenirsin:** Kural tabanlı skorlama, renk teorisini koda dökme.

> **Blok A biterse:** Elinde çalışan, gösterilebilir bir DressUpp var. Portföyde ilk demo/GIF buradan çıkar.

---

## BLOK B — Kendi Eğittiğin Modeller (data science kalbi)

### Adım 7 — Öznitelik modeli (otomatik etiketleme)
- **Yap:** DeepFashion / Fashionpedia indir, transfer learning (torchvision veya HF) ile kategori + stil sınıflandırıcı eğit. Adım 5'teki manuel dropdown'ı otomatik tahminle değiştir (kullanıcı düzeltebilir).
- **Dosya:** `notebooks/03_attribute_tagging.ipynb` → `src/tagging.py`
- **Bitti:** Yeni foto yüklenince kategori/stil otomatik tahmin ediliyor, makul doğrulukta.
- **Öğrenirsin:** Transfer learning, veri yükleyici, eğitim döngüsü, değerlendirme metrikleri (accuracy, F1).

### Adım 8 — Uyum modelini öğren (Polyvore embedding)
- **Yap:** Polyvore verisiyle bir embedding uzayı eğit — yakışan parçalar birbirine yakın düşsün. Uyum skorunu artık öğrenilmiş mesafeyle hesapla; kural tabanlıyla harmanla.
- **Dosya:** `notebooks/04_compatibility_embedding.ipynb` → `src/compatibility.py`
- **Bitti:** Öğrenilmiş model, kural tabanlıya kıyasla daha isabetli öneriler veriyor (küçük bir test setinde ölç).
- **Öğrenirsin:** Metric learning, embedding, benzerlik araması (FAISS). **Projenin en özgün kısmı.**

### Adım 9 — (İleri) Graf sinir ağıyla uyum
- **Yap:** Parçaları düğüm, kombini alt-graf sayan bir GNN ile uyumu modelle. Opsiyonel ama CV'de çok güçlü.
- **Dosya:** `notebooks/` → `src/compatibility.py`
- **Bitti:** GNN skoru embedding'e göre ölçülebilir bir iyileşme sağlıyor.
- **Öğrenirsin:** Graf sinir ağları — ileri ML.

---

## BLOK C — İleri Seviye + Yayın

### Adım 10 — İnternetten parça deneme
- **Yap:** Ürün görseli/URL'i al → işle → "geçici parça" olarak kombinde dene, uyum skorunu göster. Kalıcı gardıroba eklemek isteğe bağlı.
- **Bitti:** Satın almadan önce bir parçanın eldekilere yakışıp yakışmadığını görüyorsun.

### Adım 11 — Trend modülü (araştırma)
- **Yap:** Zaman damgalı moda verisi topla (asıl zorluk burada), attribute popülaritesini zaman serisi olarak modelle, uyum skoruna "sezonsallık çarpanı" ekle.
- **Bitti:** Öneriler "bu sezon" bilgisiyle ağırlıklanabiliyor.
- **Öğrenirsin:** Veri toplama/temizleme, zaman serisi analizi.

### Adım 12 — Yayın (deploy + PWA)
- **Yap:** Streamlit Community Cloud'a deploy; iPad/telefonda "ana ekrana ekle" ile PWA gibi aç. README'ye canlı link + demo GIF.
- **Bitti:** Herkesin açabildiği canlı bir link var.

---

## Şu anki durum

- [x] Adım 0 hazırlığı: repo iskeleti, requirements, git
- [x] Adım 1 — Arka plan kaldırma (rembg/U²-Net ile yapıldı — önce YOLOv8-seg denendi ama COCO sınıflarında "kıyafet" olmadığı için maskeler tutarsızdı, rembg'ye dönüldü)
- [ ] **Adım 2 — Baskın renk çıkarımı** ← buradan başlıyoruz

## Çalışma ritmi
Her adımı bitince commit at (`git commit -m "Adım N: ..."`). Böylece git geçmişin aynı zamanda öğrenme günlüğün olur — portföyde bu bile değerli.
