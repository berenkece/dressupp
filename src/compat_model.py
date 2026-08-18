"""
Öğrenilmiş kombin uyum modeli — Adım 8 / Aşama 1.

Tek uyum uzayı: dondurulmuş SigLIP omurgası (src/tagging.py) + üstünde küçük
eğitilebilir bir MLP başlık (CompatibilityHead). SigLIP yeniden eğitilmez,
yalnızca sabit özellik çıkarıcı olarak kullanılır; bu dosya sadece başlığın
mimarisini, kayıt/yükleme fonksiyonlarını ve çıkarım-zamanı skorlama
fonksiyonunu içerir. Eğitim/veri seti mantığı src/train_compat_model.py'de.

Type-farkındalıklı (kategori bazlı maskeleme) sürüm Aşama 2'de gelecek; bu
yüzden CompatibilityHead bilinçli olarak sade tutuldu — girdi ham 768
boyutlu embedding, çıktı L2-normalize edilmiş uyum vektörü. İleride kategori
bilgisi eklenmek istenirse input_dim büyütülüp aynı arayüz korunabilir.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence, Union

import torch
import torch.nn as nn
import torch.nn.functional as F

__all__ = [
    "CompatibilityHead",
    "save_head",
    "load_head",
    "compat_score",
    "INPUT_DIM",
    "OUTPUT_DIM",
    "DEFAULT_HEAD_PATH",
]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = PROJECT_ROOT / "models"
DEFAULT_HEAD_PATH = MODEL_DIR / "compat_head.pt"

INPUT_DIM = 768  # SigLIP (get_embedding) çıktı boyutu
HIDDEN_DIM = 256
OUTPUT_DIM = 128  # uyum uzayı boyutu


class CompatibilityHead(nn.Module):
    """Dondurulmuş SigLIP embedding'ini küçük bir uyum uzayına projekte eden MLP."""

    def __init__(self, input_dim: int = INPUT_DIM, hidden_dim: int = HIDDEN_DIM, output_dim: int = OUTPUT_DIM) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """768 boyutlu ham SigLIP embedding'ini L2-normalize uyum vektörüne çevirir."""
        return F.normalize(self.net(x), p=2, dim=-1)


def save_head(head: CompatibilityHead, path: Union[str, Path] = DEFAULT_HEAD_PATH) -> None:
    """Eğitilmiş başlığın ağırlıklarını diske kaydeder."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    torch.save(head.state_dict(), target)


def load_head(path: Union[str, Path] = DEFAULT_HEAD_PATH) -> CompatibilityHead:
    """Diskten eğitilmiş bir başlık yükler; dosya yoksa hata fırlatır."""
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(
            f"Eğitilmiş uyum başlığı bulunamadı: {target}. Önce src/train_compat_model.py çalıştırın."
        )
    head = CompatibilityHead()
    head.load_state_dict(torch.load(target, map_location="cpu"))
    head.eval()
    return head


_DEFAULT_HEAD: Optional[CompatibilityHead] = None


def _get_default_head() -> CompatibilityHead:
    """compat_score için diskteki eğitilmiş başlığı tembel yükler ve önbelleğe alır."""
    global _DEFAULT_HEAD
    if _DEFAULT_HEAD is None:
        _DEFAULT_HEAD = load_head()
    return _DEFAULT_HEAD


def _to_tensor(embedding: Union[torch.Tensor, Sequence[float]]) -> torch.Tensor:
    """Ham embedding'i (liste/np-array/tensor) float32 tensöre çevirir."""
    if isinstance(embedding, torch.Tensor):
        return embedding.to(dtype=torch.float32)
    return torch.tensor(embedding, dtype=torch.float32)


def compat_score(
    emb_a: Union[torch.Tensor, Sequence[float]],
    emb_b: Union[torch.Tensor, Sequence[float]],
    head: Optional[CompatibilityHead] = None,
) -> float:
    """İki ham SigLIP embedding'i arasındaki öğrenilmiş uyum skorunu döndürür.

    head verilmezse diskteki eğitilmiş models/compat_head.pt tembel yüklenip
    önbelleğe alınır. Skor, uyum uzayındaki kosinüs benzerliğinin [-1, 1]
    aralığından [0, 1] aralığına ölçeklenmiş halidir (1 = tam uyumlu).
    """
    active_head = head if head is not None else _get_default_head()
    a = _to_tensor(emb_a).unsqueeze(0)
    b = _to_tensor(emb_b).unsqueeze(0)

    active_head.eval()
    with torch.no_grad():
        projected_a = active_head(a)
        projected_b = active_head(b)
        cosine = F.cosine_similarity(projected_a, projected_b).item()

    return (cosine + 1.0) / 2.0


if __name__ == "__main__":
    torch.manual_seed(0)
    fresh_head = CompatibilityHead()
    dummy_a = torch.randn(INPUT_DIM)
    dummy_b = torch.randn(INPUT_DIM)

    random_score = compat_score(dummy_a, dummy_b, head=fresh_head)
    assert 0.0 <= random_score <= 1.0, "compat_score [0, 1] aralığının dışında bir değer döndürdü."
    print(f"mimari kontrolü: rastgele başlıkla skor = {random_score:.4f} (0-1 aralığında)")

    if DEFAULT_HEAD_PATH.exists():
        trained_head = load_head()
        trained_score = compat_score(dummy_a, dummy_b, head=trained_head)
        print(f"eğitilmiş başlıkla skor (rastgele vektörler): {trained_score:.4f}")
    else:
        print(f"{DEFAULT_HEAD_PATH} henüz yok; sadece mimari kontrol edildi (eğitim için src/train_compat_model.py çalıştırın).")

    print("compat model OK")
