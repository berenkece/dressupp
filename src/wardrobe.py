"""Gardırop giriş (ingest) katmanı.

Bir kıyafet fotoğrafını alıp segmentation (arka plan kaldırma), color
(baskın renk çıkarımı), schema (veri modeli) ve storage (kalıcılık)
modüllerini tek akışta birleştirerek işlenmiş, kaydedilmiş bir
ClothingItem üretir. Bu katman saf backend'dir; UI kodu içermez.
"""

from __future__ import annotations

import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from PIL import Image, UnidentifiedImageError

try:
    from src import color, segmentation, storage, utils
    from src.schema import ClothingItem, Color
except ModuleNotFoundError:  # pragma: no cover - doğrudan dosya çalıştırıldığında oluşabilir
    import color
    import segmentation
    import storage
    import utils
    from schema import ClothingItem, Color

__all__ = ["add_item", "list_wardrobe", "remove_item"]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def _open_image(image_path: str) -> Image.Image:
    """Görseli PIL ile açar; bozuk/okunamayan dosyalarda anlamlı hata fırlatır.

    PIL'in doğrudan tanımadığı formatlar (ör. HEIC/HEIF) için utils.convert_to_jpeg
    üzerinden JPEG'e çevirip öyle açar; segmentation kendi başına çağrılmadığından
    bu dönüşüm burada yapılmak zorunda.
    """
    path = Path(image_path)
    if not path.exists():
        raise ValueError(f"Görsel bulunamadı: {image_path}")

    try:
        with Image.open(path) as img:
            img.load()
            return img.copy()
    except UnidentifiedImageError as exc:
        if path.suffix.lower() not in {".heic", ".heif"}:
            raise ValueError(f"Görsel açılamadı veya bozuk: {image_path} ({exc})") from exc

        try:
            converted_path = utils.convert_to_jpeg(path, output_dir=str(PROCESSED_DIR))
            with Image.open(converted_path) as converted_img:
                converted_img.load()
                return converted_img.copy()
        except (subprocess.CalledProcessError, UnidentifiedImageError, OSError) as convert_exc:
            raise ValueError(f"Görsel açılamadı veya bozuk: {image_path} ({convert_exc})") from convert_exc
    except OSError as exc:
        raise ValueError(f"Görsel açılamadı veya bozuk: {image_path} ({exc})") from exc


def _to_schema_colors(raw_colors: List[dict]) -> List[Color]:
    """color.extract_colors çıktısını schema.Color nesnelerine çevirir."""
    return [
        Color(
            hex=str(entry.get("hex", "")),
            rgb=tuple(entry.get("rgb", (0, 0, 0))),
            hsv=tuple(entry.get("hsv", (0.0, 0.0, 0.0))),
            ratio=float(entry.get("ratio", 0.0)),
        )
        for entry in raw_colors
    ]


def _resolve_image_path(image_path: str) -> Path:
    """Göreli bir image_path'i proje köküne göre mutlak yola çevirir."""
    path = Path(image_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def add_item(
    image_path: str,
    category: Optional[str] = None,
    style: Optional[str] = None,
    season: Optional[str] = None,
    is_temporary: bool = False,
) -> ClothingItem:
    """Bir kıyafet fotoğrafını işler ve gardıroba kaydeder.

    Arka planı kaldırır, baskın renkleri çıkarır, ClothingItem oluşturur
    ve storage üzerinden kalıcı hale getirir. Oluşan parçayı döndürür.
    """
    source_image = _open_image(image_path)
    processed_image = segmentation.process(source_image)

    item_id = uuid.uuid4().hex
    saved_path = utils.save_output(
        processed_image,
        filename=f"{item_id}.png",
        output_dir=str(PROCESSED_DIR),
    )

    raw_colors = color.extract_colors(processed_image, n_colors=3)
    colors = _to_schema_colors(raw_colors)

    item = ClothingItem(
        id=item_id,
        image_path=saved_path,
        category=category or "",
        colors=colors,
        tags=[],
        added_at=datetime.now(timezone.utc).isoformat(),
        temporary=is_temporary,
        style=style,
        season=season,
    )

    storage.save_item(item)
    return item


def list_wardrobe(category: Optional[str] = None) -> List[ClothingItem]:
    """Kayıtlı kıyafetleri döndürür; category verilirse ona göre filtreler."""
    items = storage.load_items()
    if category is None:
        return items
    return [item for item in items if item.category == category]


def remove_item(item_id: str) -> bool:
    """Kıyafeti storage'dan ve işlenmiş görsel dosyasını diskten siler."""
    item = storage.get_item(item_id)
    if item is None:
        return False

    deleted = storage.delete_item(item_id)
    if deleted and item.image_path:
        image_file = _resolve_image_path(item.image_path)
        image_file.unlink(missing_ok=True)

    return deleted


if __name__ == "__main__":
    sample_path = PROJECT_ROOT / "data" / "sample_input.png"

    added_item = add_item(str(sample_path), category="top")

    assert Path(added_item.image_path).exists(), "İşlenmiş görsel diskte bulunamadı."
    assert len(added_item.colors) > 0, "Renk listesi boş."
    assert any(existing.id == added_item.id for existing in list_wardrobe()), (
        "Eklenen parça gardırop listesinde bulunamadı."
    )

    print("wardrobe OK")
    print(f"item id: {added_item.id}")
