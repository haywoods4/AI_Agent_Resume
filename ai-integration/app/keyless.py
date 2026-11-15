"""Actual local pretrained neural inference over approved skill IDs, never raw résumés."""

import asyncio
import hashlib
import json
import threading
from pathlib import Path

from app.contracts import AIMetrics
from app.providers import DependencyError, validate_assessment


class KeylessAgent:
    def __init__(self, folder=None):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        root = Path(__file__).resolve().parent.parent
        folder = Path(folder) if folder else root / "data/keyless-model"
        manifest = json.loads((root / "config/keyless-model.json").read_text())
        for source, digest in manifest["files"].items():
            if hashlib.sha256((folder / Path(source).name).read_bytes()).hexdigest() != digest:
                raise ValueError("Unverified keyless model; run setup_keyless.py")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.model = ort.InferenceSession(
            str(folder / "model.onnx"), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self.tokenizer = Tokenizer.from_file(str(folder / "tokenizer.json"))
        self.tokenizer.enable_padding()
        self.tokenizer.enable_truncation(max_length=64)
        self.lock = threading.Lock()
        self.usage = {}

    def infer(self, facts):
        import numpy as np

        if not self.lock.acquire(blocking=False):
            raise DependencyError("LOCAL_MODEL_BUSY")
        try:
            observed = {s.skill_id: s.pages for s in facts.observed_skills}
            labels = list(dict.fromkeys([*facts.required_skills, *observed]))
            encodings = self.tokenizer.encode_batch(labels)
            inputs = {
                "input_ids": np.array([e.ids for e in encodings], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in encodings], dtype=np.int64),
                "token_type_ids": np.array([e.type_ids for e in encodings], dtype=np.int64),
            }
            tokens = self.model.run(None, inputs)[0]
            mask = inputs["attention_mask"][..., None]
            vectors = (tokens * mask).sum(1) / mask.sum(1)
            vectors /= np.linalg.norm(vectors, axis=1, keepdims=True).clip(min=1e-12)
            indices = {label: i for i, label in enumerate(labels)}
            skills = []
            for skill in facts.required_skills:
                # Model similarity decides presence, not a decorative score after a rule verdict.
                matches = [
                    name
                    for name in observed
                    if float(vectors[indices[skill]] @ vectors[indices[name]]) >= 0.90
                ]
                present = bool(matches)
                skills.append(
                    {
                        "skill_id": skill,
                        "status": "MENTIONED" if present else "NOT_FOUND",
                        "evidence_pages": sorted({p for name in matches for p in observed[name]}),
                        "review_focus": "VERIFY_PROFICIENCY" if present else "REQUEST_EVIDENCE",
                    }
                )
            # Neural false matches/omissions fail closed. Never turn similarity into hiring advice.
            return validate_assessment({"skills": skills}, facts)
        except DependencyError:
            raise
        except Exception as error:
            raise DependencyError("LOCAL_MODEL_FAILED") from error
        finally:
            self.lock.release()

    async def assess(self, facts, request_id):
        result = await asyncio.to_thread(self.infer, facts)
        self.usage[request_id] = AIMetrics(cost_basis="local_compute_not_priced")
        return result

    async def close(self):
        pass
