"""Semantic tagging package."""

from .ontology import Ontology
from .rule_based import RuleBasedTagger
from .embedding_tagger import EmbeddingTagger
from .tagger import HybridTagger

__all__ = ["Ontology", "RuleBasedTagger", "EmbeddingTagger", "HybridTagger"]
