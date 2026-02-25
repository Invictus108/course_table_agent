import numpy as np
from sentence_transformers import SentenceTransformer

data = np.load("embeddings_with_text.npz", allow_pickle=True)

model = SentenceTransformer(
    "BAAI/bge-large-en-v1.5",
    device="cuda" 
)

def get_embedding(query):
    return model.encode(f"Query: {query}", normalize_embeddings=True)

embeddings = data["embeddings"]   # shape: (N, dim)
texts = data["texts"]  


def rag(query, k=5):
    query_embedding = get_embedding(query)     # get query vector
    scores = embeddings @ query_embedding      # get dot products (cosine similarity for normalized vectors)
    top_k = scores.argsort()[::-1][:k]         # get top k

    return [
        {"score": float(scores[i]), "text": texts[i]}
        for i in top_k
    ]


if __name__ == "__main__":
    res = rag("machine learning research at yale")

    for i in res:
        print(i["score"])
        print(i["text"])
        print()


