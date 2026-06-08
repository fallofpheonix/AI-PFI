from __future__ import annotations

from core.evaluation.metrics import run_evaluation


class FOAEvaluationService:
    def __init__(self, tagger):
        self._tagger = tagger

    def run(self, *, verbose: bool = True):
        return run_evaluation(self._tagger, verbose=verbose)
