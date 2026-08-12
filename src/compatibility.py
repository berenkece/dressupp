"""
Kombin uyum motoru — projenin kalbi.

Kural tabanlı, saf fonksiyonlardan oluşur: iki parça arasındaki (pairwise) ya
da bir kombinin bütünündeki (outfit) uyumu 0-100 arası bir skora çevirir.
Motor yalnızca skor üretip sıralar; giydirme/seçim kararı her zaman
kullanıcıya aittir.

İki katman:
  1. Kural tabanlı (v1, bu dosya): renk çemberi uyumu + kategori/stil/mevsim kuralları.
  2. Öğrenilmiş (v2+): Polyvore ile embedding uzayı, ileride graf sinir ağı (GNN).
"""

from typing import List, Optional, Tuple

try:
    from src.schema import ClothingItem, Color
except ModuleNotFoundError:  # pragma: no cover - doğrudan dosya çalıştırıldığında oluşabilir
    from schema import ClothingItem, Color


# --------------------------------------------------------------------------
# Ağırlıklar: pairwise skor bu üç bileşenin ağırlıklı ortalamasıdır.
# Renk en belirleyici sinyal olduğu için en yüksek ağırlığı taşır.
# --------------------------------------------------------------------------
WEIGHT_COLOR = 0.6
WEIGHT_STYLE = 0.25
WEIGHT_SEASON = 0.15

# Ton (hue) ilişkileri için puanlar (0-100). Nötr renkler (siyah/beyaz/gri/bej)
# her şeyle uyumlu kabul edildiği için en yüksek puanı alır.
SCORE_NEUTRAL = 100.0
SCORE_MONOCHROME = 95.0
SCORE_ANALOGOUS = 85.0
SCORE_COMPLEMENTARY = 80.0
SCORE_TRIADIC = 70.0
SCORE_CLASH = 35.0  # yukarıdaki ilişkilerin hiçbirine uymayan çakışan tonlar

# Doygunluk (saturation) bu eşiğin altındaysa renk "nötr" sayılır (siyah/beyaz/gri/bej).
NEUTRAL_SATURATION_MAX = 0.15

# Ton karşılaştırmasında dairesel mesafe (derece) toleransları.
MONOCHROME_TOLERANCE = 15.0
ANALOGOUS_CENTER = 30.0
ANALOGOUS_TOLERANCE = 15.0
COMPLEMENTARY_CENTER = 180.0
COMPLEMENTARY_TOLERANCE = 20.0
TRIADIC_CENTER = 120.0
TRIADIC_TOLERANCE = 15.0

# Stil/mevsim uyumu ve çelişkisi için puan/ceza (0-100 skalasında).
STYLE_MATCH_SCORE = 100.0
STYLE_CLASH_SCORE = 20.0
STYLE_NEUTRAL_SCORE = 60.0  # bilgi eksik ya da kısmen örtüşüyor

SEASON_MATCH_SCORE = 100.0
SEASON_CLASH_SCORE = 20.0
SEASON_NEUTRAL_SCORE = 70.0  # biri "all" ya da bilgi eksik

# Birbiriyle çelişen stil/mevsim çiftleri.
_CLASHING_STYLES = {frozenset({"casual", "formal"})}
_CLASHING_SEASONS = {frozenset({"summer", "winter"})}

# outfit_score içinde kategori kurallarının ağırlığı ve cezaları.
CATEGORY_DUPLICATE_PENALTY = 20.0  # aynı kategoriden fazladan her parça için
CATEGORY_MISSING_PENALTY = 15.0  # top/bottom/shoes çekirdeğinden eksik her kategori için
_CORE_CATEGORIES = ("top", "bottom", "shoes")

# outfit_score = pairwise ortalaması ile kategori cezalarının bileşimi.
OUTFIT_PAIRWISE_WEIGHT = 0.7
OUTFIT_CATEGORY_WEIGHT = 0.3


def _dominant_color(item: ClothingItem) -> Optional[Color]:
    """Bir parçanın en baskın (ratio'su en yüksek) rengini döndürür."""
    if not item.colors:
        return None
    valid = [c for c in item.colors if isinstance(c, Color)]
    if not valid:
        return None
    return max(valid, key=lambda c: c.ratio)


def _hue_distance(hue_a: float, hue_b: float) -> float:
    """İki ton (0-360) arasındaki dairesel mesafeyi (0-180) hesaplar."""
    diff = abs(hue_a - hue_b) % 360.0
    return min(diff, 360.0 - diff)


def _is_neutral(color: Color) -> bool:
    """Renk siyah/beyaz/gri/bej gibi düşük doygunluklu mu?"""
    saturation = color.hsv[1]
    return saturation <= NEUTRAL_SATURATION_MAX


def _color_harmony(color_a: Color, color_b: Color) -> Tuple[float, str]:
    """İki rengin ton ilişkisine göre 0-100 uyum puanı ve kısa gerekçe döndürür."""
    if _is_neutral(color_a) or _is_neutral(color_b):
        return SCORE_NEUTRAL, "+ nötr renk"

    distance = _hue_distance(color_a.hsv[0], color_b.hsv[0])

    if distance <= MONOCHROME_TOLERANCE:
        return SCORE_MONOCHROME, "+ monokrom ton"
    if abs(distance - ANALOGOUS_CENTER) <= ANALOGOUS_TOLERANCE:
        return SCORE_ANALOGOUS, "+ analog renk"
    if abs(distance - TRIADIC_CENTER) <= TRIADIC_TOLERANCE:
        return SCORE_TRIADIC, "+ üçlü (triadic) uyum"
    if abs(distance - COMPLEMENTARY_CENTER) <= COMPLEMENTARY_TOLERANCE:
        return SCORE_COMPLEMENTARY, "+ tümleyici renk"

    return SCORE_CLASH, "- çakışan renk tonu"


def _style_match(style_a: Optional[str], style_b: Optional[str]) -> Optional[Tuple[float, str]]:
    """Stil uyumunu puanlar; bilgi eksikse None döner (skora katılmaz)."""
    if not style_a or not style_b:
        return None
    if style_a == style_b:
        return STYLE_MATCH_SCORE, "+ aynı stil"
    if frozenset({style_a, style_b}) in _CLASHING_STYLES:
        return STYLE_CLASH_SCORE, "- çelişen stil"
    return STYLE_NEUTRAL_SCORE, "~ farklı ama çelişmeyen stil"


def _season_match(season_a: Optional[str], season_b: Optional[str]) -> Optional[Tuple[float, str]]:
    """Mevsim uyumunu puanlar; bilgi eksikse None döner (skora katılmaz)."""
    if not season_a or not season_b:
        return None
    if season_a == "all" or season_b == "all" or season_a == season_b:
        return SEASON_MATCH_SCORE, "+ uyumlu mevsim"
    if frozenset({season_a, season_b}) in _CLASHING_SEASONS:
        return SEASON_CLASH_SCORE, "- karışık mevsim"
    return SEASON_NEUTRAL_SCORE, "~ farklı ama çelişmeyen mevsim"


def pairwise_score(item_a: ClothingItem, item_b: ClothingItem) -> Tuple[float, List[str]]:
    """İki parçanın uyumunu 0-100 arası puanlar ve kısa gerekçeler döndürür.

    Eksik veri (renk/stil/mevsim) olduğunda o bileşen atlanır ve kalan
    bileşenlerin ağırlıkları kendi aralarında yeniden normalize edilir.
    """
    components: List[Tuple[float, float]] = []  # (ağırlık, puan)
    reasons: List[str] = []

    color_a, color_b = _dominant_color(item_a), _dominant_color(item_b)
    if color_a is not None and color_b is not None:
        score, reason = _color_harmony(color_a, color_b)
        components.append((WEIGHT_COLOR, score))
        reasons.append(reason)

    style_result = _style_match(item_a.style, item_b.style)
    if style_result is not None:
        score, reason = style_result
        components.append((WEIGHT_STYLE, score))
        reasons.append(reason)

    season_result = _season_match(item_a.season, item_b.season)
    if season_result is not None:
        score, reason = season_result
        components.append((WEIGHT_SEASON, score))
        reasons.append(reason)

    if not components:
        return 50.0, ["~ karşılaştırılacak yeterli bilgi yok"]

    total_weight = sum(weight for weight, _ in components)
    weighted_sum = sum(weight * score for weight, score in components)
    return round(weighted_sum / total_weight, 2), reasons


def _category_penalty(items: List[ClothingItem]) -> Tuple[float, List[str]]:
    """Kategori kurallarını kontrol eder: tekrarları cezalandırır, çekirdek eksiklerini bildirir."""
    reasons: List[str] = []
    penalty = 0.0

    counts: dict = {}
    for item in items:
        if item.category:
            counts[item.category] = counts.get(item.category, 0) + 1

    for category, count in counts.items():
        if count > 1:
            extra = count - 1
            penalty += extra * CATEGORY_DUPLICATE_PENALTY
            reasons.append(f"- {category} kategorisinden {count} parça var (fazladan {extra})")

    for category in _CORE_CATEGORIES:
        if counts.get(category, 0) == 0:
            penalty += CATEGORY_MISSING_PENALTY
            reasons.append(f"- eksik kategori: {category}")

    score = max(0.0, 100.0 - penalty)
    return score, reasons


def outfit_score(items: List[ClothingItem]) -> Tuple[float, List[str]]:
    """Bir kombinin (parça listesi) genel puanını 0-100 arasında hesaplar.

    Tüm ikili kombinasyonların pairwise_score ortalamasıyla kategori
    kurallarının (tekrar cezası, top/bottom/shoes çekirdeği) puanını birleştirir.
    """
    if len(items) < 2:
        return 0.0, ["- kombin en az iki parça içermeli"]

    reasons: List[str] = []
    pairwise_scores: List[float] = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            score, pair_reasons = pairwise_score(items[i], items[j])
            pairwise_scores.append(score)
            reasons.extend(pair_reasons)

    pairwise_avg = sum(pairwise_scores) / len(pairwise_scores)
    category_score, category_reasons = _category_penalty(items)
    reasons.extend(category_reasons)

    final_score = OUTFIT_PAIRWISE_WEIGHT * pairwise_avg + OUTFIT_CATEGORY_WEIGHT * category_score
    return round(max(0.0, min(100.0, final_score)), 2), reasons


def suggest_for(
    item: ClothingItem,
    wardrobe: List[ClothingItem],
    top_n: int = 5,
) -> List[Tuple[ClothingItem, float, List[str]]]:
    """Verilen parçaya göre gardıroptaki en uyumlu parçaları sıralayıp döndürür.

    Aynı kategoriden parçalar (ör. üste üst) elenir. Seçim yapmaz; yalnızca
    skoruna göre azalan sırada en iyi top_n adayı gerekçesiyle birlikte döndürür.
    """
    candidates = [
        candidate for candidate in wardrobe
        if candidate.id != item.id and candidate.category != item.category
    ]

    scored = [(candidate, *pairwise_score(item, candidate)) for candidate in candidates]
    scored.sort(key=lambda entry: entry[1], reverse=True)
    return scored[:top_n]


if __name__ == "__main__":
    def _make_item(item_id: str, category: str, hex_color: str, rgb, hsv, style=None, season=None) -> ClothingItem:
        color = Color(hex=hex_color, rgb=rgb, hsv=hsv, ratio=1.0)
        return ClothingItem(
            id=item_id,
            image_path=f"{item_id}.png",
            category=category,
            colors=[color],
            style=style,
            season=season,
        )

    navy_top = _make_item("navy_top", "top", "#1B2A4A", (27, 42, 74), (222.0, 0.64, 0.29), style="casual", season="all")
    beige_bottom = _make_item("beige_bottom", "bottom", "#E1D8C7", (225, 216, 199), (39.2, 0.12, 0.88), style="casual", season="all")

    red_top = _make_item("red_top", "top", "#C0392B", (192, 57, 43), (5.0, 0.78, 0.75), style="casual", season="summer")
    turquoise_bottom = _make_item("turquoise_bottom", "bottom", "#2CB5A0", (44, 181, 160), (172.0, 0.76, 0.71), style="casual", season="summer")

    second_bottom = _make_item("second_bottom", "bottom", "#333333", (51, 51, 51), (0.0, 0.0, 0.2), style="formal", season="winter")

    print("== pairwise: lacivert üst + bej alt (nötr uyum beklenir) ==")
    score_neutral, reasons_neutral = pairwise_score(navy_top, beige_bottom)
    print(score_neutral, reasons_neutral)

    print("== pairwise: kırmızı üst + turkuaz alt (tümleyici, makul skor beklenir) ==")
    score_complementary, reasons_complementary = pairwise_score(red_top, turquoise_bottom)
    print(score_complementary, reasons_complementary)

    print("== outfit_score: iki alt giyim (kategori cezası beklenir) ==")
    score_duplicate, reasons_duplicate = outfit_score([navy_top, beige_bottom, second_bottom])
    print(score_duplicate, reasons_duplicate)

    print("== outfit_score: tam kombin (top+bottom, çekirdek eksik uyarısı beklenir) ==")
    score_outfit, reasons_outfit = outfit_score([navy_top, beige_bottom])
    print(score_outfit, reasons_outfit)

    print("== suggest_for: lacivert üste gardıroptan öneri ==")
    wardrobe = [beige_bottom, red_top, turquoise_bottom, second_bottom]
    suggestions = suggest_for(navy_top, wardrobe, top_n=3)
    for candidate, score, reasons in suggestions:
        print(candidate.id, score, reasons)

    assert score_neutral > score_complementary, "nötr uyum tümleyiciden yüksek olmalı"
    assert score_duplicate < outfit_score([navy_top, beige_bottom, red_top])[0], "kategori cezası düşürmeli"
    assert suggestions[0][0].id == "beige_bottom", "en yüksek skor bej alt olmalı"

    print("compatibility OK")
