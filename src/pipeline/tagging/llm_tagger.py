"""
LLM-assisted FOA tagger.
"""

import os
import json
import logging
import re
from typing import Dict, List

from .ontology import Ontology

logger = logging.getLogger(__name__)


class LLMTagger:
    """
    LLM-assisted tagging (stretch goal).
    Requires ANTHROPIC_API_KEY or OPENAI_API_KEY env variable.
    """

    def __init__(self, ontology: Ontology):
        self.ontology = ontology

    def tag(self, text: str) -> Dict[str, List[str]]:
        # ── Try Anthropic Claude ───────────────────────────────────────────
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            try:
                import anthropic

                client = anthropic.Anthropic(api_key=api_key)
                prompt = self._build_prompt(text)
                msg = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=512,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = msg.content[0].text
                return self._parse_response(raw)
            except Exception as e:
                logger.warning(f"LLM tagging (Anthropic) failed: {e}")

        # ── Try OpenAI ─────────────────────────────────────────────────────
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI

                client = OpenAI(api_key=api_key)
                prompt = self._build_prompt(text)
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=512,
                )
                raw = resp.choices[0].message.content
                return self._parse_response(raw)
            except Exception as e:
                logger.warning(f"LLM tagging (OpenAI) failed: {e}")

        return {}

    def _build_prompt(self, text: str) -> str:
        categories = {
            cat: list(self.ontology.terms_for(cat).keys())
            for cat in self.ontology.categories
        }
        return (
            "You are a research grants classifier. "
            "Given the following Funding Opportunity Announcement text, "
            "return a JSON object with these keys: "
            + ", ".join(self.ontology.categories)
            + ". Each key should map to a list of applicable subcategory labels "
            "chosen ONLY from the allowed values shown here:\\n"
            + json.dumps(categories, indent=2)
            + "\\n\\nFOA Text (first 1500 chars):\\n"
            + text[:1500]
            + "\\n\\nRespond with ONLY valid JSON, no explanation."
        )

    def _parse_response(self, raw: str) -> Dict[str, List[str]]:
        try:
            raw = re.sub(r"```(?:json)?", "", raw).strip()
            data = json.loads(raw)
            result = {}
            for cat in self.ontology.categories:
                val = data.get(cat, [])
                if isinstance(val, list):
                    result[cat] = [str(v) for v in val]
            return result
        except Exception as e:
            logger.warning(f"Failed to parse LLM tag response: {e}")
            return {}
