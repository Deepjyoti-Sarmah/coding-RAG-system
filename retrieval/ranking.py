from collections import defaultdict

RRF_K = 60


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    *,
    k: int = RRF_K,
) -> dict[str, float]:
    scores: dict[str, float] = defaultdict(float)

    for ranked in ranked_lists:
        for rank, key in enumerate(ranked):
            scores[key] += 1.0 / (k + rank + 1)

    return dict(scores)