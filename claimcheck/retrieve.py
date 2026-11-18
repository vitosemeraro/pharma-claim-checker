"""Small BM25 retriever. No vector database needed for a document this size."""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

from .smpc import Chunk

STOPWORDS = set(
    """il lo la i gli le un una uno di da in con su per tra fra e o a al allo alla ai agli alle
    del dello della dei degli delle nel nello nella nei negli nelle è sono che non si ha
    the of and or to in on for with is are was be by as at an a""".split()
)


def tokenize(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return [t for t in re.findall(r"[a-z0-9]+(?:[.,][0-9]+)?", text) if t not in STOPWORDS]


class BM25:
    def __init__(self, chunks: list[Chunk], k1: float = 1.4, b: float = 0.75):
        self.chunks = chunks
        self.docs = [Counter(tokenize(f"{c.title} {c.text}")) for c in chunks]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lengths) / max(len(self.lengths), 1)
        df = Counter(t for d in self.docs for t in d)
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.k1, self.b = k1, b

    def search(self, query: str, k: int = 6) -> list[Chunk]:
        q = tokenize(query)
        scores = []
        for i, doc in enumerate(self.docs):
            s = 0.0
            for t in q:
                if t in doc:
                    tf = doc[t]
                    s += self.idf[t] * tf * (self.k1 + 1) / (
                        tf + self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avg)
                    )
            scores.append((s, i))
        scores.sort(reverse=True)
        return [self.chunks[i] for s, i in scores[:k] if s > 0]
