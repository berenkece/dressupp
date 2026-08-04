# DressUpp — Sanal Gardırop & Kombin Uygulaması

**Proje Planı ve Teknik Dokümantasyon**
Hazırlık tarihi: 4 Ağustos 2026

---

## 1. Özet (Elevator Pitch)

DressUpp, kullanıcının kendi dolabındaki kıyafetleri telefonuyla fotoğraflayıp dijital bir gardıroba aktardığı, sanal bir figür (avatar/manken) üzerinde kombinler denediği bir uygulamadır. Kullanıcı kıyafetleri sürükle-bırak ile giydirir; uygulama renk ve stil uyumuna göre öneriler sunar (öneriyi kabul edip etmemek kullanıcıya kalmıştır); ayrıca internetten beğenilen bir parçanın mevcut kombinlere yakışıp yakışmadığını satın almadan önce deneyebilir.

**Tek cümlelik değer önerisi:** "Dolabındaki kıyafetleri dijitalleştir, kombinleri denemeden giy, alacağın parçanın gerçekten yakışıp yakışmadığını önceden gör."

---

## 2. Problem ve Motivasyon

Çoğu insanın dolabı dolu ama "giyecek bir şeyim yok" hissi yaygın. Temel sıkıntılar:

- Dolaptaki parçaların tümü akılda tutulamadığı için hep aynı 3-4 kombin giyiliyor.
- Yeni bir parça alınırken "eldeki kıyafetlere uyar mı" belirsiz; yanlış alışveriş yapılıyor.
- Kombin denemek fiziksel olarak zaman alıyor (giy-çıkar).

DressUpp bu üç problemi tek bir görsel arayüzde çözmeyi hedefler: envanter görünürlüğü, deneme kolaylığı ve satın alma öncesi doğrulama.

---

## 3. Hedef Kullanıcı

Birincil kullanıcı, gardırobunu daha verimli kullanmak ve alışverişte daha iyi kararlar vermek isteyen kişidir (özellikle 18–35 yaş, moda/kombin ile ilgilenen, akıllı telefon kullanıcısı). Proje kişisel kullanım için başlasa da, ürün mantığı genişletilebilir bir SaaS'a uygundur.

---

## 4. MVP Kapsamı

Aşağıdaki tablo, "ilk çalışan sürümde olmalı" ile "sonraya bırakılabilir" ayrımını netleştirir.

**MVP'de var (v1):**

- Kıyafet fotoğrafı yükleme (telefon/bilgisayar)
- Otomatik arka plan kaldırma
- Kategori + renk etiketleme (yarı otomatik)
- Sanal figür üzerinde katmanlı giydirme (üst / alt / ayakkabı / dış giyim / aksesuar)
- Kombin oluşturma ve kaydetme
- Kural tabanlı kombin önerisi (renk & kategori uyumu)

**v2'de gelir:**

- İnternetten seçilen parçayı (URL/görsel) kombinde deneme
- AI destekli öneri (model tabanlı, doğal dil açıklamalı)
- Kombin geçmişi ve "en çok giyilenler" istatistiği

**v3 / gelecek:**

- Gerçek vücut ölçülerine göre kişisel avatar
- Sosyal paylaşım / arkadaştan oy alma
- Hava durumuna ve takvime göre günlük kombin önerisi

---

## 5. Özellikler ve Kullanıcı Akışları

### 5.1 Gardıroba kıyafet ekleme

1. Kullanıcı "Kıyafet Ekle" der ve fotoğraf çeker/yükler.
2. Sistem arka planı otomatik kaldırır ve şeffaf PNG üretir.
3. Sistem kıyafeti otomatik sınıflandırmaya çalışır: kategori (üst/alt/ayakkabı/dış/aksesuar), baskın renk(ler), mevsim.
4. Kullanıcı önerilen etiketleri onaylar veya düzeltir.
5. Parça gardıroba kaydedilir.

**Kabul kriteri:** Yüklenen fotoğrafın arka planı temizlenmiş, doğru kategoriye düşmüş ve gardırop ızgarasında görünüyor olmalı.

### 5.2 Bebeği/mankeni giydirme

Sanal figür, üst üste binen katmanlardan oluşur (z-index sıralı): arka plan → vücut/avatar → alt giyim → üst giyim → dış giyim → ayakkabı → aksesuar. Kullanıcı gardıroptan bir parçayı seçince ilgili katmana yerleşir. Aynı kategoriden yeni parça seçilince eskisi değişir.

**Kabul kriteri:** Kullanıcı 4-5 parçalık tam bir kombini figür üzerinde tutarlı katman sırasıyla görebilmeli.

### 5.3 Kombin kaydetme

Oluşturulan kombin isim + etiketle (örn. "iş", "günlük", "gece") kaydedilir. Kayıtlı kombinler ayrı bir sekmede küçük önizlemelerle listelenir.

### 5.4 AI / öneri akışı

İki katmanlı çalışır:

- **Kural tabanlı (her zaman aktif, offline):** Seçili bir parçaya renk çemberi uyumu (tamamlayıcı, analog, nötr) ve kategori kurallarıyla eşleşen parçaları "bunlar yakışır" olarak öne çıkarır.
- **AI destekli (opsiyonel, v2):** Gardırop + seçili parça bir modele verilir; model doğal dille "neden yakıştığını" açıklayan öneriler döner.

**Kritik kural:** Öneri her zaman öneridir. Seçim tamamen kullanıcıya aittir; sistem otomatik giydirme yapmaz, sadece işaretler/sıralar.

### 5.5 İnternetten parça deneme (v2)

1. Kullanıcı bir ürün görselini yükler veya ürün URL'sini yapıştırır.
2. Sistem görseli işler (arka plan kaldırma + etiketleme), ama kalıcı gardıroba eklemez — "geçici deneme" olarak işaretler.
3. Kullanıcı bu geçici parçayı mevcut kombinlerinde dener.
4. Öneri motoru "eldeki parçalarla uyum skoru" gösterir.
5. Kullanıcı isterse parçayı gardıroba kalıcı ekler (satın aldığında).

---

## 6. Teknik Mimari

### 6.1 Önerilen teknoloji yığını

Not: Kullanıcı ilk aşamada plan/dokümantasyon istediği için burada gerekçeleriyle bir öneri sunulmuştur; uygulama aşamasında değiştirilebilir.

| Katman | Öneri | Gerekçe |
|---|---|---|
| Ön yüz | React + TypeScript | Bileşen tabanlı, sürükle-bırak arayüz için ideal, CV'de güçlü |
| Stil/UI | Tailwind CSS | Hızlı, tutarlı responsive tasarım |
| Katmanlı giydirme | HTML5 Canvas veya katmanlı DOM/SVG | z-index kontrolü ve parça değişimi kolay |
| Arka plan kaldırma | `rembg` (Python, U²-Net) veya `@imgly/background-removal` (tarayıcıda) | Otomatik, açık kaynak; ilki sunucuda, ikincisi client-side |
| Backend (v2) | Node.js + Express veya Python FastAPI | Gardırop kalıcılığı, AI proxy |
| Veritabanı (v2) | PostgreSQL veya SQLite (başlangıç) | Yapılandırılmış gardırop/kombin verisi |
| Dosya depolama | Yerel / S3 uyumlu bucket | Kıyafet PNG'leri |
| AI öneri (v2) | Bir görsel-dil modeli API'si | Doğal dilli kombin önerisi |

### 6.2 Arka plan kaldırma pipeline

```
Fotoğraf yükle
   ↓
Boyut normalize et (örn. max 1024px, EXIF döndürme düzelt)
   ↓
Arka plan kaldırma modeli (rembg / imgly)  →  şeffaf PNG
   ↓
Kırpma (bounding box'a göre otomatik trim)
   ↓
Baskın renk çıkarımı (k-means, ~3 renk)
   ↓
Kategori tahmini (görsel sınıflandırma modeli — v2; v1'de manuel/dropdown)
   ↓
Gardıroba kaydet (metadata + PNG)
```

v1'de kategori tahmini yerine kullanıcı dropdown'dan seçebilir; bu MVP'yi hızlandırır. Renk çıkarımı ise kural tabanlı öneri için gerekli olduğundan v1'de yer alır.

### 6.3 Öneri motoru mantığı

**Kural tabanlı skorlama (v1):**

Bir kombinin uyum skoru şu bileşenlerden hesaplanabilir:

- **Renk uyumu:** Seçili parçaların baskın renkleri HSV renk çemberine oturtulur. Tamamlayıcı (karşıt), analog (komşu) veya nötr (siyah/beyaz/gri/bej) ilişkiler pozitif puan; çakışan/uyumsuz tonlar negatif puan alır.
- **Kategori kuralları:** Her katmandan en fazla bir parça; eksik zorunlu katman (örn. alt giyim yok) uyarı verir.
- **Stil/etiket uyumu:** "spor" bir üst ile "resmi" bir ayakkabı düşük puan alır (etiket tabanlı).
- **Mevsim tutarlılığı:** Kışlık dış giyim + yazlık alt karışımı düşük puan.

Toplam skor 0–100 arası normalize edilip yıldız/renk göstergesiyle sunulur.

**AI destekli (v2):** Gardırop parçalarının metadata'sı ve seçili parça bir modele gönderilir. Prompt, modelden "en iyi 3 kombin + her biri için kısa gerekçe" ister. Sonuç kural tabanlı skorla harmanlanır; kullanıcıya iki kaynak da şeffafça gösterilir.

### 6.4 Veri modeli (özet)

**ClothingItem**
- id, kullanıcı_id
- görsel_url (şeffaf PNG)
- kategori (enum: top, bottom, shoes, outerwear, accessory)
- renkler (baskın renk listesi, hex)
- etiketler (stil: casual/formal/sport; mevsim)
- eklenme_tarihi
- geçici_mi (internetten deneme parçası için)

**Outfit**
- id, kullanıcı_id
- isim, etiketler
- parça_id_listesi (katman → ClothingItem)
- önizleme_görseli
- oluşturulma_tarihi

**User (v2)**
- id, isim, avatar_ayarları (vücut tipi, ten tonu vb.)

### 6.5 Önerilen klasör yapısı (v1, React)

```
dressupp/
├── src/
│   ├── components/
│   │   ├── Wardrobe/        (gardırop ızgarası, yükleme)
│   │   ├── Dressing/        (katmanlı figür, sürükle-bırak)
│   │   ├── Outfits/         (kayıtlı kombinler)
│   │   └── Suggestions/     (öneri paneli)
│   ├── engine/
│   │   ├── colorUtils.ts    (renk çıkarımı, uyum hesabı)
│   │   └── recommender.ts   (kural tabanlı skorlama)
│   ├── services/
│   │   └── backgroundRemoval.ts
│   ├── data/                (yerel state / mock veriler)
│   └── App.tsx
├── public/
└── package.json
```

---

## 7. Aşamalı Yol Haritası

**Aşama 0 — Kurulum (1 hafta):** Repo, React+TS+Tailwind iskeleti, boş sayfa yönlendirmesi, tasarım taslakları (wireframe).

**Aşama 1 — Statik giydirme (1–2 hafta):** Katmanlı figür bileşeni, hazır (mock) kıyafet PNG'leriyle sürükle-bırak giydirme. Henüz yükleme yok.

**Aşama 2 — Gardırop + yükleme (2 hafta):** Fotoğraf yükleme, arka plan kaldırma entegrasyonu, renk çıkarımı, manuel kategori seçimi, gardırop ızgarası.

**Aşama 3 — Kombin + kural tabanlı öneri (2 hafta):** Kombin kaydetme, öneri motoru, uyum skoru göstergesi.

**Aşama 4 — İnternet parçası deneme + AI (2–3 hafta):** Geçici parça akışı, AI öneri API entegrasyonu, doğal dilli açıklamalar.

**Aşama 5 — Cila (sürekli):** Responsive/mobil uyum, boş durumlar, hata mesajları, erişilebilirlik, küçük animasyonlar.

Bu tempo haftada birkaç saat çalışmayla ~2,5–3 aylık bir öğrenme + geliştirme sürecine denk gelir.

---

## 8. CV'de Nasıl Anlatılır

Projeyi CV/portföyde şu çerçevede sunmak etkilidir:

> **DressUpp — Sanal Gardırop & AI Kombin Asistanı** (Kişisel Proje)
> Kullanıcının kendi kıyafetlerini fotoğraflayıp dijitalleştirdiği, sanal figür üzerinde kombin denediği ve renk/stil uyumuna göre öneri aldığı bir web uygulaması geliştirdim. Otomatik arka plan kaldırma (U²-Net), k-means ile baskın renk çıkarımı ve HSV renk çemberi tabanlı bir öneri motoru kurdum. React + TypeScript ön yüz, katmanlı canvas giydirme ve opsiyonel AI destekli öneri katmanı içerir.

**Bu proje sana şu becerileri kazandırır (ve CV'de gösterir):**

- Ön yüz mühendisliği: React, TypeScript, durum yönetimi, sürükle-bırak, canvas/SVG
- Görüntü işleme: arka plan kaldırma, renk analizi, sınıflandırma
- Algoritma tasarımı: kural tabanlı öneri/skorlama motoru
- AI entegrasyonu: model API'si, prompt tasarımı, sonuç harmanlama
- Ürün düşüncesi: MVP kapsamı belirleme, aşamalı teslim, kullanıcı akışı tasarımı

Portföy için ekstra puan: kısa bir demo videosu/GIF, canlı bir deploy linki (Vercel/Netlify) ve README'de mimari diyagramı.

---

## 9. Riskler ve Dikkat Edilecekler

- **Arka plan kaldırma kalitesi:** Karmaşık/desenli kıyafetlerde kenar hataları olabilir; kullanıcıya küçük bir manuel rötuş imkanı bırakmak faydalı.
- **Kombin görselinin gerçekçiliği:** Düz PNG bindirme, gerçek bir "giydirme" gibi durmayabilir; v1 için kabul edilebilir, ileride warping/AI try-on düşünülebilir.
- **İnternet görselleri:** Telif ve ürün görseli kullanımına dikkat; kişisel/deneme kapsamında tutmak güvenli.
- **AI maliyeti:** API çağrıları ücretli; kural tabanlı katmanı varsayılan tutup AI'ı isteğe bağlı yapmak maliyeti kontrol eder.
- **Kapsam kayması:** En büyük risk MVP'yi şişirmek. Aşama 1-3'e sadık kalıp önce çalışan bir çekirdek çıkarmak kritik.

---

## 10. Sonraki Adım

Bu plan onaylanırsa bir sonraki somut adım, **Aşama 0 + Aşama 1**'i kurmaktır: React iskeleti ve mock kıyafetlerle çalışan katmanlı giydirme prototipi. İstersen bunu doğrudan çalışan bir kod olarak kurmaya başlayabilirim.
