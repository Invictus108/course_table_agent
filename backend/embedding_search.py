from sentence_transformers import SentenceTransformer


model = SentenceTransformer('intfloat/e5-small-v2')


def embed(text):
    return model.encode(text)