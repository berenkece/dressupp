# DressUpp 👗

Kendi dolabındaki kıyafetleri dijitalleştirip sanal bir figür üzerinde kombin yapabildiğin, renk ve stil uyumuna göre öneri alabildiğin bir moda-AI projesi.

> Kişisel bir moda + veri bilimi projesi. Amaç: fotoğraftan kıyafet anlama, kombin uyumu öğrenme ve trend modellemeyi uçtan uca bir sistemde birleştirmek.

## Ne yapıyor?

- 📸 Telefon/bilgisayardan kıyafet fotoğrafı yükleme
- ✂️ Otomatik arka plan kaldırma (şeffaf PNG)
- 🏷️ Otomatik etiketleme: kategori, baskın renk, stil
- 🧍 Sanal figür üzerinde katmanlı giydirme
- 💡 Kombin önerisi (kural tabanlı + öğrenilmiş uyum modeli) — seçim her zaman kullanıcıda
- 🛒 İnternetten seçilen bir parçayı satın almadan önce kombinde deneme *(planlı)*
- 📈 Zamanın trendlerine göre öneri ağırlıklandırma *(araştırma modülü, planlı)*

## Teknik kararlar

| Konu | Karar | Neden |
|---|---|---|
| Platform | Web + PWA | iPad/telefonda uygulama gibi açılır, App Store gerekmez |
| Dil / ML | Python + PyTorch | CV/DS için standart |
| Prototip arayüz | Streamlit | UI kodu yazmadan çalışan demo, önceden deneyim var |
| Cilalı arayüz | React (sonraki aşama) | Ürünleşince |
| Segmentasyon | Hazır model (rembg / U²-Net) | Eğitmeye gerek yok |
| Öznitelik etiketleme | DeepFashion / Fashionpedia + transfer learning | Kendi eğittiğimiz ilk model |
| Kombin uyumu | Polyvore → embedding → GNN | Projenin kalbi |
| Trend | Zaman serisi araştırma modülü | En son aşama |

## ML yol haritası

Üç halka, her biri bir öncekinin çıktısına dayanıyor:

1. **Etiketleme** — Fotoğrafı yapılandırılmış veriye çevir (kategori, renk, stil vektörü).
2. **Uyum** — Etiketlenmiş parçaların birbirine yakışıp yakışmadığını öğren (embedding uzayı, sonra graf sinir ağı).
3. **Trend** — Uyum kararını "bu sezon" bilgisiyle ağırlıklandır (zaman damgalı veri).

> Kısaca: **etikete öğret → yakışmayı öğret → zamanı öğret.**

## Kurulum

```bash
# Sanal ortam
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Bağımlılıklar
pip install -r requirements.txt

# Prototipi çalıştır
streamlit run app.py
```

Ardından tarayıcıda açılan Streamlit arayüzünden bir kıyafet fotoğrafı yükleyip arka plan kaldırma + renk çıkarımını deneyebilirsin.

## Klasör yapısı

```
dressupp/
├── app.py                  # Streamlit prototip giriş noktası
├── src/
│   ├── segmentation.py     # Arka plan kaldırma (hazır model)
│   ├── color.py            # Baskın renk çıkarımı (k-means)
│   ├── tagging.py          # Öznitelik sınıflandırma (eğitilecek)
│   ├── compatibility.py    # Kombin uyum motoru (kural tabanlı + öğrenilmiş)
│   └── schema.py           # Veri modelleri (ClothingItem, Outfit)
├── notebooks/              # Deney ve eğitim defterleri
├── data/                   # Veri setleri (git'e girmez)
├── models/                 # Eğitilmiş model ağırlıkları (git'e girmez)
├── docs/                   # Plan ve teknik dokümantasyon
├── requirements.txt
└── README.md
```

## Durum

🚧 Erken geliştirme — Aşama 1: prototip iskelet + arka plan kaldırma + renk çıkarımı.

## Lisans

MIT
