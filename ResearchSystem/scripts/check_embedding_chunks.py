"""Check real CPU-model chunk limits and tail preservation on dense symbols."""
import json
import os
from pathlib import Path

root = Path(__file__).resolve().parents[1]
os.environ.setdefault('HF_HOME', str(root / 'data/hf-home'))
os.environ.setdefault('HF_XET_CACHE', str(root / 'data/hf-xet'))
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
from book_research.embeddings import CPUEmbeddings

encoder = CPUEmbeddings(root / 'data/models')
text = ('Covariant tensor T_mu_nu = alpha^2 + beta_3; Lorentz transformations. ' * 200) + ' UNIQUE_FINAL_MARKER'
parts = list(encoder.chunk_text(text))
assert len(parts) > 1
assert 'UNIQUE_FINAL_MARKER' in parts[-1]
lengths = [len(encoder.tokenizer.encode(part).ids) for part in parts]
assert max(lengths) <= 512
vectors = encoder.embed([parts[0], parts[-1]])
assert len(vectors) == 2 and all(len(vector) == 384 for vector in vectors)
report = {'status':'passed','chunks':len(parts),'max_chunk_tokens':max(lengths),
          'last_marker_preserved':True,'dimensions':384}
(root / 'reports/embedding-chunk-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
