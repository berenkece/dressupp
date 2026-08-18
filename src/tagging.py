"""
Öznitelik etiketleme (zero-shot sınıflandırma).

Marqo/marqo-fashionSigLIP modeliyle bir kıyafet görseline kategori, stil ve
mevsim etiketlerini eğitimsiz (zero-shot) olarak atar. Her öznitelik kendi
aday cümle kümesiyle ayrı ayrı sorgulanır; kazanan cümle schema'daki iç
değere (CATEGORIES/STYLES/SEASONS) geri eşlenir.

Bu modül saf backend mantığıdır; UI kodu ve dosya yazma (kayıt) içermez.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
from PIL import Image

try:
    from src.schema import CATEGORIES, SEASONS, STYLES, ClothingItem
except ModuleNotFoundError:  # pragma: no cover - doğrudan dosya çalıştırıldığında oluşabilir
    from schema import CATEGORIES, SEASONS, STYLES, ClothingItem

__all__ = ["predict_attributes", "tag_item", "get_embedding", "CONFIDENCE_THRESHOLD"]

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_MODEL_NAME = "Marqo/marqo-fashionSigLIP"

# Bir özniteliğin en yüksek olasılığı bu eşiğin altındaysa model "emin değil"
# sayılır ve o öznitelik None döner (kullanıcı elle düzeltir). 0.3, kaç aday
# olursa olsun rastgele tahminden belirgin şekilde yüksek ama modele aşırı
# güvenmeyen, elle seçilmiş bir denge noktasıdır.
CONFIDENCE_THRESHOLD = 0.3

# Cümle -> iç değer eşlemeleri. Doğal cümleler ("a formal outfit") ham
# kelimelerden ("formal") daha iyi CLIP/SigLIP metin gömmesi üretir.
_CATEGORY_PROMPTS: Dict[str, str] = {
    "a top, t-shirt, shirt, or blouse": "top",
    "bottom wear such as pants, jeans, shorts, or a skirt": "bottom",
    "a pair of shoes": "shoes",
    "an outerwear jacket or coat": "outerwear",
    "a fashion accessory such as a bag, hat, belt, or jewelry": "accessory",
}

_STYLE_PROMPTS: Dict[str, str] = {
    "a casual, everyday outfit": "casual",
    "a formal, elegant outfit": "formal",
    "sportswear or athletic clothing": "sport",
}

_SEASON_PROMPTS: Dict[str, str] = {
    "clothing suited for warm spring weather": "spring",
    "clothing suited for hot summer weather": "summer",
    "clothing suited for cool autumn weather": "autumn",
    "clothing suited for cold winter weather": "winter",
    "clothing suitable for all seasons, season-neutral": "all",
}

assert set(_CATEGORY_PROMPTS.values()) == set(CATEGORIES)
assert set(_STYLE_PROMPTS.values()) == set(STYLES)
assert set(_SEASON_PROMPTS.values()) == set(SEASONS)

_MODEL: Optional[Any] = None
_PROCESSOR: Optional[Any] = None


def _get_model_and_processor() -> Tuple[Any, Any]:
    """Modeli ve processor'ü tembel yükler; sonraki çağrılarda önbellekten döner."""
    global _MODEL, _PROCESSOR
    if _MODEL is None or _PROCESSOR is None:
        from transformers import AutoModel, AutoProcessor

        _MODEL = AutoModel.from_pretrained(_MODEL_NAME, trust_remote_code=True)
        _PROCESSOR = AutoProcessor.from_pretrained(_MODEL_NAME, trust_remote_code=True)
        _MODEL.eval()
    return _MODEL, _PROCESSOR


def _ensure_rgb(img: Image.Image) -> Image.Image:
    """Şeffaf görseli beyaz zemine kompozit edip RGB'ye çevirir.

    Şeffaf pikselleri doğrudan convert("RGB") ile çevirmek, alfa kanalının
    altındaki rastgele (genelde siyah) RGB değerlerini ortaya çıkarır ve
    modeli yanıltabilir; bu yüzden önce beyaz bir zemine kompozit ediyoruz.
    """
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    return img.convert("RGB") if img.mode != "RGB" else img


def _encode_image(img: Image.Image) -> torch.Tensor:
    """Görseli normalize edilmiş SigLIP görsel gömmesine çevirir."""
    model, processor = _get_model_and_processor()
    rgb_image = _ensure_rgb(img)
    inputs = processor(images=[rgb_image], return_tensors="pt")
    with torch.no_grad():
        return model.get_image_features(inputs["pixel_values"], normalize=True)


def _classify(image_features: torch.Tensor, prompts: Dict[str, str]) -> Dict[str, float]:
    """Bir aday cümle kümesine karşı zero-shot benzerlik olasılıklarını hesaplar."""
    model, processor = _get_model_and_processor()
    sentences = list(prompts.keys())
    labels = list(prompts.values())

    text_inputs = processor(text=sentences, return_tensors="pt", padding="max_length")
    with torch.no_grad():
        text_features = model.get_text_features(text_inputs["input_ids"], normalize=True)
        probs = (100.0 * image_features @ text_features.T).softmax(dim=-1)

    return dict(zip(labels, (float(p) for p in probs.squeeze(0).tolist())))


def _best_label(scores: Dict[str, float]) -> Optional[str]:
    """En yüksek olasılıklı etiketi döndürür; eşik altındaysa None (emin değil)."""
    best_label = max(scores, key=scores.get)
    if scores[best_label] < CONFIDENCE_THRESHOLD:
        return None
    return best_label


def predict_attributes(img: Image.Image) -> Dict[str, Any]:
    """Görsele kategori/stil/mevsim etiketlerini zero-shot olarak atar.

    Üç öznitelik ayrı ayrı sorgulanır. Dönüş: tahmin edilen değerler ve her
    adayın güven skorları. Bir özniteliğin en yüksek olasılığı
    CONFIDENCE_THRESHOLD altındaysa o öznitelik None döner.
    """
    image_features = _encode_image(img)

    category_scores = _classify(image_features, _CATEGORY_PROMPTS)
    style_scores = _classify(image_features, _STYLE_PROMPTS)
    season_scores = _classify(image_features, _SEASON_PROMPTS)

    return {
        "category": _best_label(category_scores),
        "style": _best_label(style_scores),
        "season": _best_label(season_scores),
        "scores": {
            "category": category_scores,
            "style": style_scores,
            "season": season_scores,
        },
    }


def get_embedding(img: Image.Image) -> List[float]:
    """Görselin normalize edilmiş SigLIP gömme vektörünü döndürür (uyum modeli için)."""
    return _encode_image(img).squeeze(0).tolist()


def _resolve_image_path(image_path: str) -> Path:
    """Göreli bir image_path'i proje köküne göre mutlak yola çevirir."""
    path = Path(image_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def tag_item(item: ClothingItem) -> ClothingItem:
    """item.image_path'teki görseli okuyup tahmin edilen etiketlerle item'ı günceller.

    Kayıt (storage) işlemini çağıran taraf yapar; bu fonksiyon yalnızca
    ClothingItem nesnesini günceller ve döndürür. Model emin değilse (None)
    ilgili alan mevcut değerinde bırakılır.
    """
    image_path = _resolve_image_path(item.image_path)
    with Image.open(image_path) as opened:
        opened.load()
        img = opened.copy()

    result = predict_attributes(img)
    item.category = result["category"] or item.category
    item.style = result["style"] if result["style"] is not None else item.style
    item.season = result["season"] if result["season"] is not None else item.season
    return item


if __name__ == "__main__":
    sample_path = PROJECT_ROOT / "data" / "processed" / "fd9693e72bff47a4ad730c9df65a131f.png"

    with Image.open(sample_path) as opened_sample:
        opened_sample.load()
        sample_img = opened_sample.copy()

    prediction = predict_attributes(sample_img)
    print(f"category: {prediction['category']} (scores={prediction['scores']['category']})")
    print(f"style: {prediction['style']} (scores={prediction['scores']['style']})")
    print(f"season: {prediction['season']} (scores={prediction['scores']['season']})")

    if prediction["category"] == "top":
        print("tagging OK")
    else:
        print("tagging: beklenen 'top' kategorisi en yüksek çıkmadı, kontrol edin.")
