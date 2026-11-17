"""Optional CPU semantic model. Download/cache location is explicitly selected."""
import hashlib
import math
from pathlib import Path


class CPUEmbeddings:
    max_words = 180

    def __init__(self, cache_dir: Path):
        import ssl
        import httpx
        from huggingface_hub import set_client_factory
        from fastembed import TextEmbedding
        self.model = 'sentence-transformers/all-MiniLM-L6-v2'
        cache_dir = Path(cache_dir).resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)
        set_client_factory(lambda: httpx.Client(verify=ssl.create_default_context(), follow_redirects=True, timeout=60))
        self.encoder = TextEmbedding(model_name=self.model, cache_dir=str(cache_dir), threads=2)
        from tokenizers import Tokenizer
        self.tokenizer = Tokenizer.from_str(self.encoder.model.tokenizer.to_str())
        self.tokenizer.no_padding()
        self.tokenizer.no_truncation()
        artifacts = sorted(cache_dir.rglob('*.onnx'))
        if not artifacts:
            raise ValueError('No downloaded ONNX model found in cache')
        digest = hashlib.sha256()
        for artifact in artifacts:
            with artifact.open('rb') as stream:
                digest.update(hashlib.file_digest(stream, 'sha256').digest())
        self._identity = self.model + '@' + digest.hexdigest()

    def identity(self):
        return self._identity

    def chunk_text(self, text):
        offsets = self.tokenizer.encode(text, add_special_tokens=False).offsets
        start = 0
        while start < len(offsets):
            end = min(start + 384, len(offsets))
            passage = text[offsets[start][0]:offsets[end-1][1]].strip()
            if passage:
                yield passage
            if end == len(offsets):
                break
            start = end - 48

    def embed(self, texts):
        # FastEmbed's MiniLM tokenizer truncates at a small context window.
        # Reject oversized inputs rather than silently dropping source text.
        for text in texts:
            if len(self.tokenizer.encode(text).ids) > 512:
                raise ValueError('MiniLM input reaches 512-token limit. Use shorter chunks/query or Ollama.')
        vectors = [vector.tolist() for vector in self.encoder.embed(texts, batch_size=16)]
        if len(vectors) != len(texts) or any(not vector or not all(math.isfinite(v) for v in vector) for vector in vectors):
            raise ValueError('Invalid embedding response')
        return vectors
