"""
Kombin uyum motoru — projenin kalbi.

İki katman:
  1. Kural tabanlı (v1): renk çemberi uyumu + kategori/stil/mevsim kuralları -> 0-100 skor.
  2. Öğrenilmiş (v2+): Polyvore ile embedding uzayı, ileride graf sinir ağı (GNN).

Kritik: öneri her zaman öneridir; seçim kullanıcıya aittir.

TODO: kural tabanlı skorlama; sonra embedding eğitimi.
"""
