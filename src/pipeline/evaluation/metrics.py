"""
Evaluation module.

Provides:
  - A hard-coded evaluation dataset of FOA text snippets with gold-standard tags
  - Precision, recall, F1 calculation per category
  - A run_evaluation() function that tests the HybridTagger
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Gold-standard evaluation dataset ─────────────────────────────────────────

EVAL_DATASET = [
    {
        "id": "eval-001",
        "description": "NIH R01 grant for cancer immunotherapy research using machine learning for biomarker discovery in pediatric patients.",
        "gold_tags": {
            "research_domains": ["biomedical", "computer_science"],
            "methods_approaches": ["experimental", "ai_ml"],
            "populations": ["pediatric"],
            "sponsor_themes": ["basic_research"],
        },
    },
    {
        "id": "eval-002",
        "description": "NSF grant to develop novel algorithms for distributed computing systems with applications in climate modeling.",
        "gold_tags": {
            "research_domains": ["computer_science", "physical_sciences"],
            "methods_approaches": ["computational"],
            "populations": [],
            "sponsor_themes": ["basic_research"],
        },
    },
    {
        "id": "eval-003",
        "description": "USDA funding for sustainable agriculture research targeting food security in rural low-income communities in developing countries.",
        "gold_tags": {
            "research_domains": ["agriculture", "environmental"],
            "methods_approaches": ["observational"],
            "populations": ["rural", "low_income", "global"],
            "sponsor_themes": ["translation"],
        },
    },
    {
        "id": "eval-004",
        "description": "DOD SBIR award for engineering design and prototype development of advanced composite materials for aerospace applications.",
        "gold_tags": {
            "research_domains": ["engineering", "physical_sciences"],
            "methods_approaches": ["engineering_design"],
            "populations": [],
            "sponsor_themes": ["innovation"],
        },
    },
    {
        "id": "eval-005",
        "description": "Career development award for early career investigators studying mental health disparities among African American veterans using mixed methods.",
        "gold_tags": {
            "research_domains": ["health_services", "social_sciences"],
            "methods_approaches": ["mixed_methods"],
            "populations": ["minority", "veterans"],
            "sponsor_themes": ["early_career", "equity_inclusion"],
        },
    },
    {
        "id": "eval-006",
        "description": "Fellowship program to train graduate students and postdoctoral researchers in data science, machine learning, and AI ethics with focus on broadening participation.",
        "gold_tags": {
            "research_domains": ["computer_science"],
            "methods_approaches": ["ai_ml"],
            "populations": [],
            "sponsor_themes": ["workforce_development", "equity_inclusion"],
        },
    },
    {
        "id": "eval-007",
        "description": "Systematic review and meta-analysis of randomized controlled trials evaluating telemedicine interventions for elderly patients with chronic conditions.",
        "gold_tags": {
            "research_domains": ["health_services"],
            "methods_approaches": ["systematic_review", "experimental"],
            "populations": ["elderly"],
            "sponsor_themes": ["translation"],
        },
    },
    {
        "id": "eval-008",
        "description": "Multi-institutional consortium grant to establish shared research infrastructure including biobank, core facility, and data repository for genomics studies.",
        "gold_tags": {
            "research_domains": ["biomedical"],
            "methods_approaches": [],
            "populations": [],
            "sponsor_themes": ["infrastructure", "collaboration"],
        },
    },
]


# ── Metrics ───────────────────────────────────────────────────────────────────

@dataclass
class CategoryMetrics:
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    support: int = 0       # number of gold positive items
    tp: int = 0
    fp: int = 0
    fn: int = 0


@dataclass
class EvaluationReport:
    per_category: Dict[str, CategoryMetrics] = field(default_factory=dict)
    macro_precision: float = 0.0
    macro_recall: float = 0.0
    macro_f1: float = 0.0
    n_examples: int = 0

    def to_dict(self) -> dict:
        return {
            "n_examples": self.n_examples,
            "macro_precision": round(self.macro_precision, 4),
            "macro_recall": round(self.macro_recall, 4),
            "macro_f1": round(self.macro_f1, 4),
            "per_category": {
                cat: {
                    "precision": round(m.precision, 4),
                    "recall": round(m.recall, 4),
                    "f1": round(m.f1, 4),
                    "support": m.support,
                }
                for cat, m in self.per_category.items()
            },
        }

    def print_summary(self):
        print("\n" + "=" * 60)
        print("  FOA TAGGING EVALUATION REPORT")
        print("=" * 60)
        print(f"  Examples evaluated : {self.n_examples}")
        print(f"  Macro Precision    : {self.macro_precision:.4f}")
        print(f"  Macro Recall       : {self.macro_recall:.4f}")
        print(f"  Macro F1           : {self.macro_f1:.4f}")
        print("-" * 60)
        for cat, m in self.per_category.items():
            print(
                f"  {cat:<25}  P={m.precision:.3f}  R={m.recall:.3f}  "
                f"F1={m.f1:.3f}  (support={m.support})"
            )
        print("=" * 60 + "\n")


# ── Evaluation runner ─────────────────────────────────────────────────────────

def compute_metrics(
    predictions: List[Dict[str, List[str]]],
    gold_labels: List[Dict[str, List[str]]],
) -> EvaluationReport:
    """Compute per-category and macro precision/recall/F1."""
    all_cats = set()
    for g in gold_labels:
        all_cats.update(g.keys())

    per_cat: Dict[str, CategoryMetrics] = {}

    for cat in all_cats:
        tp = fp = fn = support = 0
        for pred, gold in zip(predictions, gold_labels):
            pred_set = set(pred.get(cat, []))
            gold_set = set(gold.get(cat, []))
            tp += len(pred_set & gold_set)
            fp += len(pred_set - gold_set)
            fn += len(gold_set - pred_set)
            support += len(gold_set)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)
              if (precision + recall) > 0 else 0.0)
        per_cat[cat] = CategoryMetrics(
            precision=precision, recall=recall, f1=f1,
            support=support, tp=tp, fp=fp, fn=fn,
        )

    cats_with_support = [m for m in per_cat.values() if m.support > 0]
    macro_p = sum(m.precision for m in cats_with_support) / len(cats_with_support) if cats_with_support else 0
    macro_r = sum(m.recall for m in cats_with_support) / len(cats_with_support) if cats_with_support else 0
    macro_f = sum(m.f1 for m in cats_with_support) / len(cats_with_support) if cats_with_support else 0

    return EvaluationReport(
        per_category=per_cat,
        macro_precision=macro_p,
        macro_recall=macro_r,
        macro_f1=macro_f,
        n_examples=len(predictions),
    )


def run_evaluation(tagger, dataset: list = None, verbose: bool = True) -> EvaluationReport:
    """
    Run the tagger against the eval dataset and return an EvaluationReport.

    :param tagger: Any tagger with a .tag_text(str) -> dict method
    :param dataset: Optional custom dataset; defaults to EVAL_DATASET
    :param verbose: Print summary to stdout
    """
    dataset = dataset or EVAL_DATASET
    predictions = []
    gold_labels = []

    for example in dataset:
        text = example["description"]
        pred = tagger.tag_text(text)
        predictions.append(pred)
        gold_labels.append(example["gold_tags"])
        logger.debug(f"[{example['id']}] pred={pred}")

    report = compute_metrics(predictions, gold_labels)
    if verbose:
        report.print_summary()

    return report
