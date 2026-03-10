import numpy as np


def cosine_similarity(a, b):

    a = np.array(a)
    b = np.array(b)

    denom = np.linalg.norm(a) * np.linalg.norm(b)

    if denom == 0:
        return 0

    return np.dot(a, b) / denom


def mmr(query_embedding, docs, k=5, lambda_param=0.7):

    selected = []
    candidates = docs.copy()

    while len(selected) < k and candidates:

        mmr_scores = []

        for doc in candidates:

            relevance = cosine_similarity(query_embedding, doc["embedding"])

            diversity = 0
            if selected:
                diversity = max(
                    cosine_similarity(doc["embedding"], s["embedding"])
                    for s in selected
                )

            score = lambda_param * relevance - (1 - lambda_param) * diversity
            mmr_scores.append(score)

        best_index = np.argmax(mmr_scores)
        print(best_index)

        selected.append(candidates.pop(best_index))

    return selected