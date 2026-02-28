from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class KB:
    def __init__(self, kb_dir: str | None):
        self.docs = []
        self.vectorizer = None
        self.matrix = None
        if kb_dir:
            p = Path(kb_dir)
            if p.exists():
                for fp in p.rglob("*"):
                    if fp.is_file() and fp.suffix.lower() in {".md", ".txt"}:
                        text = fp.read_text(encoding="utf-8", errors="ignore").strip()
                        if text:
                            self.docs.append((str(fp), text))
        if self.docs:
            self.vectorizer = TfidfVectorizer(stop_words="english", max_features=12000)
            self.matrix = self.vectorizer.fit_transform([d[1] for d in self.docs])

    def search(self, query: str, k: int = 3):
        if not self.docs or not self.vectorizer or self.matrix is None:
            return []
        q = self.vectorizer.transform([query])
        sims = cosine_similarity(q, self.matrix)[0]
        idxs = np.argsort(-sims)[:k]
        out = []
        for i in idxs:
            if sims[i] <= 0:
                continue
            path, txt = self.docs[i]
            out.append({"path": path, "score": float(sims[i]), "snippet": txt[:280].replace("\n", " ")})
        return out
