"""
Arka plan kaldırma / segmentasyon.

Hazır model kullanılır (rembg / U²-Net) — eğitim yok.
Girdi: PIL.Image  ->  Çıktı: şeffaf arka planlı PNG (PIL.Image, RGBA)

TODO: rembg.remove sarmalayıcısı, kırpma (bounding box trim).
"""
