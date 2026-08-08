"""DressUpp veri modelleri.

Bu modül, gardırop verilerinin hafif ve taşınabilir JSON temsiline karşılık
gelebilecek temel nesneleri tanımlar. Dışarıdaki katmanlar (ör. depolama veya
arayüz) bu sınıfları kullanarak veriyi diskten okur ve yazar.
"""

from typing import Any, Dict, List, Optional, Tuple, Union


class Color:
    """Bir görüntüden çıkarılan baskın rengi temsil eder."""

    def __init__(
        self,
        hex: str,
        rgb: Tuple[int, int, int],
        hsv: Tuple[float, float, float],
        ratio: float = 0.0,
    ) -> None:
        self.hex = hex
        self.rgb = tuple(rgb)
        self.hsv = tuple(hsv)
        self.ratio = ratio

    def to_dict(self) -> Dict[str, Any]:
        """Nesneyi JSON'a yazılabilir sözlüğe çevir."""
        return {
            "hex": self.hex,
            "rgb": list(self.rgb),
            "hsv": list(self.hsv),
            "ratio": self.ratio,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Color":
        """Sözlükten nesne oluşturur."""
        if not isinstance(data, dict):
            raise TypeError("Color.from_dict için sözlük beklenir.")

        return cls(
            hex=str(data.get("hex", "")),
            rgb=tuple(data.get("rgb", (0, 0, 0))),
            hsv=tuple(data.get("hsv", (0.0, 0.0, 0.0))),
            ratio=float(data.get("ratio", 0.0)),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Color):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    def __repr__(self) -> str:
        return f"Color(hex={self.hex!r}, ratio={self.ratio!r})"


class ClothingItem:
    """Tek bir kıyafet parçası."""

    def __init__(
        self,
        id: str,
        image_path: str,
        category: str,
        colors: Optional[List[Union[Color, str]]] = None,
        tags: Optional[List[str]] = None,
        added_at: Optional[str] = None,
        temporary: bool = False,
        style: Optional[str] = None,
        season: Optional[str] = None,
    ) -> None:
        self.id = id
        self.image_path = image_path
        self.category = category
        self.colors = colors or []
        self.tags = tags or []
        self.added_at = added_at
        self.temporary = temporary
        self.style = style
        self.season = season

    def to_dict(self) -> Dict[str, Any]:
        """Nesneyi JSON'a yazılabilir sözlüğe çevir."""
        return {
            "id": self.id,
            "image_path": self.image_path,
            "category": self.category,
            "colors": [c.to_dict() if isinstance(c, Color) else c for c in self.colors],
            "tags": list(self.tags),
            "added_at": self.added_at,
            "temporary": self.temporary,
            "style": self.style,
            "season": self.season,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClothingItem":
        """Sözlükten nesne oluşturur."""
        if not isinstance(data, dict):
            raise TypeError("ClothingItem.from_dict için sözlük beklenir.")

        raw_colors = data.get("colors", [])
        colors: List[Union[Color, str]] = []
        if isinstance(raw_colors, list):
            for entry in raw_colors:
                colors.append(Color.from_dict(entry) if isinstance(entry, dict) else entry)

        tags = data.get("tags", [])

        return cls(
            id=str(data["id"]),
            image_path=str(data.get("image_path", data.get("imagePath", ""))),
            category=str(data.get("category", "")),
            colors=colors,
            tags=list(tags) if isinstance(tags, list) else [],
            added_at=data.get("added_at", data.get("addedAt")),
            temporary=bool(data.get("temporary", False)),
            style=data.get("style"),
            season=data.get("season"),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ClothingItem):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    def __repr__(self) -> str:
        return f"ClothingItem(id={self.id!r}, category={self.category!r})"


class Outfit:
    """Bir kombin kümesi; parça kimlikleri ve önizleme yolu saklanır."""

    def __init__(
        self,
        id: str,
        name: str,
        tags: Optional[List[str]] = None,
        item_ids: Optional[List[str]] = None,
        preview_path: Optional[str] = None,
        created_at: Optional[str] = None,
    ) -> None:
        self.id = id
        self.name = name
        self.tags = tags or []
        self.item_ids = item_ids or []
        self.preview_path = preview_path
        self.created_at = created_at

    def to_dict(self) -> Dict[str, Any]:
        """Kombini JSON'a yazılabilir sözlüğe çevir."""
        return {
            "id": self.id,
            "name": self.name,
            "tags": list(self.tags),
            "item_ids": list(self.item_ids),
            "preview_path": self.preview_path,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Outfit":
        """Sözlükten nesne oluşturur."""
        if not isinstance(data, dict):
            raise TypeError("Outfit.from_dict için sözlük beklenir.")

        item_ids = data.get("item_ids", data.get("items", data.get("pieces", [])))
        if isinstance(item_ids, list):
            normalized_ids = []
            for item in item_ids:
                if isinstance(item, dict):
                    normalized_ids.append(str(item.get("id", "")))
                else:
                    normalized_ids.append(str(item))
        else:
            normalized_ids = []

        return cls(
            id=str(data["id"]),
            name=str(data.get("name", "")),
            tags=list(data.get("tags", [])) if isinstance(data.get("tags", []), list) else [],
            item_ids=normalized_ids,
            preview_path=data.get("preview_path", data.get("previewPath")),
            created_at=data.get("created_at", data.get("createdAt")),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Outfit):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    def __repr__(self) -> str:
        return f"Outfit(id={self.id!r}, name={self.name!r})"


__all__ = ["Color", "ClothingItem", "Outfit"]
