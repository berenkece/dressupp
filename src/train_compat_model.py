"""
CompatibilityHead için eğitim scripti — Adım 8 / Aşama 1.

Marqo/polyvore veri setini (Hugging Face) kullanır. Veri setinin gerçek
şeması `datasets` ile incelenerek doğrulandı: her satır {"image": PIL,
"category": str, "text": str, "item_ID": str} içerir; item_ID formatı
"{outfit_id}_{sıra}" (ör. "100002074_3") — orijinal Polyvore kombin (outfit)
gruplamasının doğrudan karşılığı. Aynı outfit_id'ye sahip parçalar aynı
kombinde giyilmiş, dolayısıyla birbiriyle uyumlu kabul edilir.

Akış:
  1. Parquet parçalarını indirip görselleri + item_ID'leri yükle (ya da
     önbellekteki embedding'leri kullan, görselleri hiç indirme).
  2. SigLIP embedding'lerini bir kez, toplu (batched) olarak çıkar ve
     models/polyvore_embeddings.npy + models/polyvore_item_ids.json'a
     kaydet. Sonraki her çalıştırmada (ve eğitimin her epoch'unda) bu
     önbellekten okunur; SigLIP bir daha çalıştırılmaz.
  3. item_ID'lerden outfit gruplarını çıkar, kombin (outfit) bazında
     train/val/test böl — item bazında değil, sızıntı (leakage) olmasın.
  4. Pozitif (aynı kombin) ve negatif (farklı kombin, rastgele) çiftlerle
     CompatibilityHead'i kontrastif kayıpla eğit; en iyi val AUC'a sahip
     ağırlıkları models/compat_head.pt olarak kaydet.
  5. Test kümesinde AUC ve FITB (boşluk doldurma) ile değerlendir, sonuçları
     yazdır.
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from sklearn.metrics import roc_auc_score

try:
    from src import tagging
    from src.compat_model import (
        CompatibilityHead,
        DEFAULT_HEAD_PATH,
        MODEL_DIR,
        compat_score,
        save_head,
    )
except ModuleNotFoundError:  # pragma: no cover - doğrudan dosya çalıştırıldığında oluşabilir
    import tagging
    from compat_model import (
        CompatibilityHead,
        DEFAULT_HEAD_PATH,
        MODEL_DIR,
        compat_score,
        save_head,
    )

__all__ = ["main"]

DATASET_NAME = "Marqo/polyvore"
DATASET_TOTAL_SHARDS = 6

EMBEDDINGS_PATH = MODEL_DIR / "polyvore_embeddings.npy"
ITEM_IDS_PATH = MODEL_DIR / "polyvore_item_ids.json"

# Tüm veri seti ~94k görsel; bu makinede SigLIP çıkarımı toplu modda bile
# ~25ms/görsel sürüyor (~40 dk tüm veri seti için). Prototip (Aşama 1) için
# 1 parça (~15.7k görsel, ~3k kombin) birkaç dakikada bitiyor ve anlamlı
# bir AUC/FITB tahmini için yeterli; --num-shards ile artırılabilir.
DEFAULT_NUM_SHARDS = 1
EMBED_BATCH_SIZE = 32

TRAIN_FRACTION = 0.8
VAL_FRACTION = 0.1
# kalan (1 - TRAIN_FRACTION - VAL_FRACTION) test için ayrılır.

RANDOM_SEED = 42
MARGIN = 0.2  # negatif çiftler için kontrastif kayıp marjı
LEARNING_RATE = 1e-3
NUM_EPOCHS = 30
TRAIN_BATCH_SIZE = 256
NEG_PER_POS = 1  # her pozitif çift için üretilecek negatif çift sayısı

FITB_NUM_CANDIDATES = 4
RANDOM_BASELINE_AUC = 0.5
RANDOM_BASELINE_FITB = 1.0 / FITB_NUM_CANDIDATES


def _outfit_id(item_id: str) -> str:
    """item_ID'den ("outfit_id_sıra") kombin kimliğini çıkarır."""
    return item_id.rsplit("_", 1)[0]


def load_polyvore_items(num_shards: int) -> Tuple[List[Image.Image], List[str]]:
    """Marqo/polyvore parquet parçalarını indirip görselleri ve item_ID'leri döndürür."""
    from datasets import load_dataset

    num_shards = max(1, min(num_shards, DATASET_TOTAL_SHARDS))
    shard_files = [f"data/data-{i:05d}-of-{DATASET_TOTAL_SHARDS:05d}.parquet" for i in range(num_shards)]

    # verification_mode="no_checks": repodaki dataset_info metadata'sı tüm
    # 6 parçanın (94k örnek) toplamını beklediği için, kasıtlı olarak alt
    # küme (num_shards parça) yüklerken datasets bunu tutarsızlık sanıp hata
    # fırlatıyor; bu bilinçli bir alt küme seçimi olduğu için kontrolü kapatıyoruz.
    dataset = load_dataset(
        DATASET_NAME, data_files={"data": shard_files}, split="data", verification_mode="no_checks"
    )

    images = list(dataset["image"])
    item_ids = list(dataset["item_ID"])
    return images, item_ids


def compute_embeddings(images: Sequence[Image.Image], batch_size: int = EMBED_BATCH_SIZE) -> np.ndarray:
    """Görselleri toplu (batched) olarak SigLIP embedding'lerine çevirir.

    tagging.get_embedding tek görsel işler; burada aynı model/processor
    önbelleğini (tagging._get_model_and_processor) toplu modda kullanarak
    binlerce görsel için ciddi bir hız kazancı sağlıyoruz.
    """
    model, processor = tagging._get_model_and_processor()
    chunks: List[np.ndarray] = []

    for start in range(0, len(images), batch_size):
        batch = images[start : start + batch_size]
        rgb_batch = [tagging._ensure_rgb(img) for img in batch]
        inputs = processor(images=rgb_batch, return_tensors="pt")
        with torch.no_grad():
            features = model.get_image_features(inputs["pixel_values"], normalize=True)
        chunks.append(features.numpy().astype(np.float32))

    return np.concatenate(chunks, axis=0)


def save_embeddings_cache(embeddings: np.ndarray, item_ids: List[str]) -> None:
    """Önceden hesaplanmış embedding'leri ve item_ID sırasını diske yazar."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    np.save(EMBEDDINGS_PATH, embeddings)
    ITEM_IDS_PATH.write_text(json.dumps(item_ids), encoding="utf-8")


def load_embeddings_cache() -> Tuple[np.ndarray, List[str]]:
    """Önbellekteki embedding'leri ve item_ID sırasını yükler."""
    embeddings = np.load(EMBEDDINGS_PATH)
    item_ids = json.loads(ITEM_IDS_PATH.read_text(encoding="utf-8"))
    return embeddings, item_ids


def build_outfits(item_ids: Sequence[str]) -> Dict[str, List[int]]:
    """item_ID listesinden outfit_id -> [embedding indeksleri] eşlemesi çıkarır."""
    outfits: Dict[str, List[int]] = defaultdict(list)
    for idx, item_id in enumerate(item_ids):
        outfits[_outfit_id(item_id)].append(idx)
    return dict(outfits)


def split_outfits(
    outfits: Dict[str, List[int]],
    train_fraction: float = TRAIN_FRACTION,
    val_fraction: float = VAL_FRACTION,
    seed: int = RANDOM_SEED,
) -> Tuple[Dict[str, List[int]], Dict[str, List[int]], Dict[str, List[int]]]:
    """Kombinleri (item değil, outfit_id bazında) train/val/test'e böler; sızıntı önlenir."""
    outfit_ids = sorted(outfits.keys())
    rng = random.Random(seed)
    rng.shuffle(outfit_ids)

    n = len(outfit_ids)
    n_train = int(n * train_fraction)
    n_val = int(n * val_fraction)

    train_ids = outfit_ids[:n_train]
    val_ids = outfit_ids[n_train : n_train + n_val]
    test_ids = outfit_ids[n_train + n_val :]

    return (
        {oid: outfits[oid] for oid in train_ids},
        {oid: outfits[oid] for oid in val_ids},
        {oid: outfits[oid] for oid in test_ids},
    )


def sample_positive_pairs(outfits: Dict[str, List[int]]) -> List[Tuple[int, int]]:
    """Aynı kombindeki tüm parça ikililerini pozitif (uyumlu) çift olarak üretir."""
    pairs: List[Tuple[int, int]] = []
    for indices in outfits.values():
        if len(indices) < 2:
            continue
        pairs.extend(itertools.combinations(indices, 2))
    return pairs


def sample_negative_pairs(
    outfits: Dict[str, List[int]], num_pairs: int, rng: random.Random
) -> List[Tuple[int, int]]:
    """Farklı kombinlerden rastgele ikişer parça seçerek negatif (uyumsuz) çift üretir."""
    outfit_ids = list(outfits.keys())
    if len(outfit_ids) < 2:
        return []

    pairs: List[Tuple[int, int]] = []
    for _ in range(num_pairs):
        outfit_a, outfit_b = rng.sample(outfit_ids, 2)
        idx_a = rng.choice(outfits[outfit_a])
        idx_b = rng.choice(outfits[outfit_b])
        pairs.append((idx_a, idx_b))
    return pairs


def contrastive_loss(
    projected_a: torch.Tensor, projected_b: torch.Tensor, labels: torch.Tensor, margin: float = MARGIN
) -> torch.Tensor:
    """Pozitif çiftlerde kosinüs benzerliğini artırır, negatiflerde marjın altına iter."""
    cosine = F.cosine_similarity(projected_a, projected_b)
    positive_loss = labels * (1.0 - cosine)
    negative_loss = (1.0 - labels) * torch.clamp(cosine - margin, min=0.0)
    return (positive_loss + negative_loss).mean()


def _pairs_to_tensors(
    embeddings: torch.Tensor, pairs: List[Tuple[int, int]], label: float
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    idx_a = torch.tensor([p[0] for p in pairs], dtype=torch.long)
    idx_b = torch.tensor([p[1] for p in pairs], dtype=torch.long)
    labels = torch.full((len(pairs),), label, dtype=torch.float32)
    return embeddings[idx_a], embeddings[idx_b], labels


def _auc_for_pairs(
    head: CompatibilityHead,
    embeddings: torch.Tensor,
    positive_pairs: List[Tuple[int, int]],
    negative_pairs: List[Tuple[int, int]],
) -> float:
    """Pozitif+negatif çiftler üzerinde kosinüs skorlarıyla AUC hesaplar."""
    head.eval()
    with torch.no_grad():
        pos_a, pos_b, pos_labels = _pairs_to_tensors(embeddings, positive_pairs, 1.0)
        neg_a, neg_b, neg_labels = _pairs_to_tensors(embeddings, negative_pairs, 0.0)

        scores_pos = F.cosine_similarity(head(pos_a), head(pos_b)).numpy()
        scores_neg = F.cosine_similarity(head(neg_a), head(neg_b)).numpy()

    scores = np.concatenate([scores_pos, scores_neg])
    labels = np.concatenate([pos_labels.numpy(), neg_labels.numpy()])
    return float(roc_auc_score(labels, scores))


def train_head(
    embeddings_np: np.ndarray,
    train_outfits: Dict[str, List[int]],
    val_outfits: Dict[str, List[int]],
    num_epochs: int = NUM_EPOCHS,
    batch_size: int = TRAIN_BATCH_SIZE,
    learning_rate: float = LEARNING_RATE,
    seed: int = RANDOM_SEED,
) -> CompatibilityHead:
    """CompatibilityHead'i kontrastif kayıpla eğitir; en iyi val AUC'lu ağırlıkları döndürür."""
    torch.manual_seed(seed)
    rng = random.Random(seed)

    embeddings = torch.from_numpy(embeddings_np)

    train_positive = sample_positive_pairs(train_outfits)
    train_negative = sample_negative_pairs(train_outfits, len(train_positive) * NEG_PER_POS, rng)
    print(f"eğitim çiftleri: {len(train_positive)} pozitif, {len(train_negative)} negatif")

    val_positive = sample_positive_pairs(val_outfits)
    val_negative = sample_negative_pairs(val_outfits, len(val_positive), rng)

    train_pairs = [(a, b, 1.0) for a, b in train_positive] + [(a, b, 0.0) for a, b in train_negative]

    head = CompatibilityHead()
    optimizer = torch.optim.Adam(head.parameters(), lr=learning_rate)

    best_val_auc = -1.0
    best_state = head.state_dict()

    for epoch in range(1, num_epochs + 1):
        rng.shuffle(train_pairs)
        head.train()
        epoch_loss = 0.0
        num_batches = 0

        for start in range(0, len(train_pairs), batch_size):
            batch = train_pairs[start : start + batch_size]
            idx_a = torch.tensor([p[0] for p in batch], dtype=torch.long)
            idx_b = torch.tensor([p[1] for p in batch], dtype=torch.long)
            labels = torch.tensor([p[2] for p in batch], dtype=torch.float32)

            projected_a = head(embeddings[idx_a])
            projected_b = head(embeddings[idx_b])
            loss = contrastive_loss(projected_a, projected_b, labels)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()
            num_batches += 1

        val_auc = _auc_for_pairs(head, embeddings, val_positive, val_negative)
        if val_auc > best_val_auc:
            best_val_auc = val_auc
            best_state = {k: v.clone() for k, v in head.state_dict().items()}

        if epoch == 1 or epoch % 5 == 0 or epoch == num_epochs:
            print(f"  epoch {epoch:>3}: loss={epoch_loss / max(num_batches, 1):.4f}  val_auc={val_auc:.4f}")

    head.load_state_dict(best_state)
    head.eval()
    print(f"en iyi val AUC: {best_val_auc:.4f}")
    return head


def evaluate_auc(
    head: CompatibilityHead, embeddings_np: np.ndarray, test_outfits: Dict[str, List[int]], seed: int = RANDOM_SEED
) -> float:
    """Test kümesinde gerçek kombinleri vs rastgele çiftleri ayırt etme başarısını AUC ile ölçer."""
    rng = random.Random(seed + 1)
    embeddings = torch.from_numpy(embeddings_np)
    positive_pairs = sample_positive_pairs(test_outfits)
    negative_pairs = sample_negative_pairs(test_outfits, len(positive_pairs), rng)
    return _auc_for_pairs(head, embeddings, positive_pairs, negative_pairs)


def evaluate_fitb(
    head: CompatibilityHead,
    embeddings_np: np.ndarray,
    test_outfits: Dict[str, List[int]],
    num_candidates: int = FITB_NUM_CANDIDATES,
    seed: int = RANDOM_SEED,
) -> float:
    """Boşluk doldurma (fill-in-the-blank) doğruluğu: eksik parça + N aday arasından doğrusunu seçme.

    Her uygun test kombini için bir parça "boşluk" olarak çıkarılır, geri
    kalanı bağlam (context) olur. Doğru parça + (num_candidates - 1) rastgele
    dışarıdan aday arasından, bağlamla ortalama uyum skoru en yüksek olan
    seçilir; doğru tahmin oranı döndürülür.
    """
    rng = random.Random(seed + 2)
    embeddings = torch.from_numpy(embeddings_np)
    head.eval()

    all_outfit_ids = list(test_outfits.keys())
    eligible_outfits = [oid for oid in all_outfit_ids if len(test_outfits[oid]) >= 2]

    correct = 0
    total = 0

    with torch.no_grad():
        for outfit_id in eligible_outfits:
            indices = test_outfits[outfit_id]
            blank_idx = rng.choice(indices)
            context_indices = [i for i in indices if i != blank_idx]

            other_outfits = [oid for oid in all_outfit_ids if oid != outfit_id]
            distractor_pool = rng.sample(other_outfits, min(num_candidates - 1, len(other_outfits)))
            distractor_indices = [rng.choice(test_outfits[oid]) for oid in distractor_pool]

            candidate_indices = [blank_idx] + distractor_indices
            context_tensor = head(embeddings[context_indices])

            candidate_scores = []
            for cand_idx in candidate_indices:
                cand_proj = head(embeddings[cand_idx].unsqueeze(0))
                mean_sim = F.cosine_similarity(cand_proj.expand_as(context_tensor), context_tensor).mean().item()
                candidate_scores.append(mean_sim)

            predicted = int(np.argmax(candidate_scores))
            if predicted == 0:  # candidate_indices[0] doğru parça
                correct += 1
            total += 1

    return correct / total if total > 0 else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="CompatibilityHead'i Marqo/polyvore ile eğitir.")
    parser.add_argument("--num-shards", type=int, default=DEFAULT_NUM_SHARDS, help=f"1-{DATASET_TOTAL_SHARDS} arası parquet parça sayısı")
    parser.add_argument("--force-recompute-embeddings", action="store_true", help="Önbellek varsa bile embedding'leri yeniden hesapla")
    parser.add_argument("--epochs", type=int, default=NUM_EPOCHS)
    args = parser.parse_args()

    if EMBEDDINGS_PATH.exists() and ITEM_IDS_PATH.exists() and not args.force_recompute_embeddings:
        print(f"embedding önbelleği bulundu, yükleniyor: {EMBEDDINGS_PATH}")
        embeddings_np, item_ids = load_embeddings_cache()
    else:
        print(f"Marqo/polyvore indiriliyor ve işleniyor ({args.num_shards} parça)...")
        images, item_ids = load_polyvore_items(args.num_shards)
        print(f"{len(images)} görsel yüklendi, SigLIP embedding'leri çıkarılıyor...")
        embeddings_np = compute_embeddings(images)
        save_embeddings_cache(embeddings_np, item_ids)
        print(f"embedding önbelleği kaydedildi: {EMBEDDINGS_PATH}")

    outfits = build_outfits(item_ids)
    print(f"{len(item_ids)} parça, {len(outfits)} kombin")

    train_outfits, val_outfits, test_outfits = split_outfits(outfits)
    print(f"bölünme: train={len(train_outfits)} val={len(val_outfits)} test={len(test_outfits)} kombin")

    head = train_head(embeddings_np, train_outfits, val_outfits, num_epochs=args.epochs)
    save_head(head, DEFAULT_HEAD_PATH)
    print(f"başlık kaydedildi: {DEFAULT_HEAD_PATH}")

    test_auc = evaluate_auc(head, embeddings_np, test_outfits)
    test_fitb = evaluate_fitb(head, embeddings_np, test_outfits)

    print(f"\nTEST AUC:  {test_auc:.4f}  (rastgele baseline: {RANDOM_BASELINE_AUC:.2f})")
    print(f"TEST FITB: {test_fitb:.4f}  (rastgele baseline: {RANDOM_BASELINE_FITB:.2f})")

    # Tek bir rastgele çift AUC'un altında yatan olasılığı yansıtmaz (ör. AUC
    # 0.68 iken tek bir çift %32 ihtimalle ters sırada çıkabilir); bu yüzden
    # birkaç örneğin ortalamasını gösteriyoruz.
    demo_rng = random.Random(RANDOM_SEED + 3)
    positive_pairs = sample_positive_pairs(test_outfits)
    negative_pairs = sample_negative_pairs(test_outfits, min(20, len(positive_pairs)), demo_rng)
    demo_positive = demo_rng.sample(positive_pairs, min(20, len(positive_pairs)))
    if demo_positive:
        pos_scores = [compat_score(embeddings_np[a], embeddings_np[b], head=head) for a, b in demo_positive]
        print(f"örnek pozitif çiftler (n={len(pos_scores)}) ortalama skoru: {sum(pos_scores) / len(pos_scores):.4f}")
    if negative_pairs:
        neg_scores = [compat_score(embeddings_np[a], embeddings_np[b], head=head) for a, b in negative_pairs]
        print(f"örnek negatif çiftler (n={len(neg_scores)}) ortalama skoru: {sum(neg_scores) / len(neg_scores):.4f}")

    if test_auc > RANDOM_BASELINE_AUC + 0.05 and test_fitb > RANDOM_BASELINE_FITB + 0.05:
        print("compat model OK")
    else:
        print("UYARI: AUC/FITB rastgele baseline'dan yeterince yüksek değil, model kontrol edilmeli.")


if __name__ == "__main__":
    main()
