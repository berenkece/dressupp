"""Gardırop verilerinin kalıcı depolama katmanı.

ClothingItem ve Outfit nesneleri JSON dosyasında saklanır. Bu modül tek
sorumlu yer olarak verinin okunması/yazılmasını yönetir.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from src.schema import ClothingItem, Outfit
except ModuleNotFoundError:  # pragma: no cover - doğrudan dosya çalıştırıldığında oluşabilir
    from schema import ClothingItem, Outfit

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "wardrobe.json"


def _resolve_db_path(db_path: Optional[str] = None) -> Path:
    """İstenen veritabanı yolunu projeye göre çözer."""
    if db_path is None:
        resolved = DEFAULT_DB_PATH
    else:
        candidate = Path(db_path)
        if candidate.is_absolute():
            resolved = candidate
        else:
            resolved = (Path(__file__).resolve().parent.parent / candidate).resolve()
    return resolved


def _read_db(db_path: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """JSON veritabanını okur; dosya yoksa veya bozuksa güvenli varsayılan döner."""
    path = _resolve_db_path(db_path)

    if not path.exists():
        return {"items": [], "outfits": []}

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return {"items": [], "outfits": []}

    if not isinstance(data, dict):
        return {"items": [], "outfits": []}

    items = data.get("items", [])
    outfits = data.get("outfits", [])

    if not isinstance(items, list):
        items = []
    if not isinstance(outfits, list):
        outfits = []

    return {"items": items, "outfits": outfits}


def _write_db(payload: Dict[str, List[Dict[str, Any]]], db_path: Optional[str] = None) -> None:
    """Veriyi atomik biçimde yazar; yarım yazma riski ortadan kalkar."""
    path = _resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_name(f".{path.name}.tmp")
    try:
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except OSError:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise


def save_item(item: ClothingItem, db_path: Optional[str] = None) -> None:
    """Tek bir kıyafeti ekler veya aynı id ile günceller."""
    db = _read_db(db_path)
    items = db["items"]
    item_dict = item.to_dict()

    for index, current in enumerate(items):
        if isinstance(current, dict) and current.get("id") == item_dict["id"]:
            items[index] = item_dict
            break
    else:
        items.append(item_dict)

    db["items"] = items
    _write_db(db, db_path)


def load_items(db_path: Optional[str] = None) -> List[ClothingItem]:
    """Tüm kıyafetleri diskten okur ve model nesnelerine çevirir."""
    raw_items = _read_db(db_path).get("items", [])
    items: List[ClothingItem] = []

    for entry in raw_items:
        if not isinstance(entry, dict):
            continue
        try:
            items.append(ClothingItem.from_dict(entry))
        except (TypeError, ValueError, KeyError):
            continue

    return items


def get_item(item_id: str, db_path: Optional[str] = None) -> Optional[ClothingItem]:
    """Verilen id ile kıyafeti döner; yoksa None döner."""
    for item in load_items(db_path):
        if item.id == item_id:
            return item
    return None


def delete_item(item_id: str, db_path: Optional[str] = None) -> bool:
    """Kıyafeti siler; silme başarılıysa True döner."""
    db = _read_db(db_path)
    before = len(db["items"])
    db["items"] = [
        entry for entry in db["items"] if not (isinstance(entry, dict) and entry.get("id") == item_id)
    ]

    if len(db["items"]) == before:
        return False

    _write_db(db, db_path)
    return True


def save_outfit(outfit: Outfit, db_path: Optional[str] = None) -> None:
    """Tek bir kombin kaydeder; aynı id varsa üzerine yazar."""
    db = _read_db(db_path)
    outfits = db["outfits"]
    outfit_dict = outfit.to_dict()

    for index, current in enumerate(outfits):
        if isinstance(current, dict) and current.get("id") == outfit_dict["id"]:
            outfits[index] = outfit_dict
            break
    else:
        outfits.append(outfit_dict)

    db["outfits"] = outfits
    _write_db(db, db_path)


def load_outfits(db_path: Optional[str] = None) -> List[Outfit]:
    """Tüm kombinleri diskten okur."""
    raw_outfits = _read_db(db_path).get("outfits", [])
    outfits: List[Outfit] = []

    for entry in raw_outfits:
        if not isinstance(entry, dict):
            continue
        try:
            outfits.append(Outfit.from_dict(entry))
        except (TypeError, ValueError, KeyError):
            continue

    return outfits


def get_outfit(outfit_id: str, db_path: Optional[str] = None) -> Optional[Outfit]:
    """Verilen id ile kombin döner; yoksa None döner."""
    for outfit in load_outfits(db_path):
        if outfit.id == outfit_id:
            return outfit
    return None


def delete_outfit(outfit_id: str, db_path: Optional[str] = None) -> bool:
    """Kombini siler; silme başarılıysa True döner."""
    db = _read_db(db_path)
    before = len(db["outfits"])
    db["outfits"] = [
        entry for entry in db["outfits"] if not (isinstance(entry, dict) and entry.get("id") == outfit_id)
    ]

    if len(db["outfits"]) == before:
        return False

    _write_db(db, db_path)
    return True


if __name__ == "__main__":
    """Kısa self-test: item persistence ve CRUD davranışını doğrular."""
    test_db = Path(__file__).resolve().parent.parent / "data" / "tmp_wardrobe_test.json"

    try:
        if test_db.exists():
            test_db.unlink()

        item = ClothingItem(
            id="item-001",
            image_path="data/processed/item-001.png",
            category="top",
            colors=["#ffb3ba", "#ffffff"],
            tags=["casual", "summer"],
            added_at="2026-08-08T10:00:00",
            temporary=False,
        )

        save_item(item, str(test_db))
        loaded_items = load_items(str(test_db))
        assert len(loaded_items) == 1
        assert loaded_items[0].to_dict() == item.to_dict()
        assert get_item(item.id, str(test_db)).to_dict() == item.to_dict()

        deleted = delete_item(item.id, str(test_db))
        assert deleted is True
        assert load_items(str(test_db)) == []
        assert get_item(item.id, str(test_db)) is None

        print("storage OK")
    finally:
        if test_db.exists():
            test_db.unlink()
