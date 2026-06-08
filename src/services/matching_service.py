import logging
from typing import List

from core.models import FOARecord, ResearcherProfile
from core.storage.exporter import FOAStore
from core.storage.researcher_store import ResearcherStore

logger = logging.getLogger(__name__)


class MatchingService:
    def __init__(self, foa_store: FOAStore | None = None):
        self.foa_store = foa_store or FOAStore()
        self.researcher_store = ResearcherStore()

    def get_matches_for_profile(self, profile: ResearcherProfile, limit: int = 5) -> List[FOARecord]:
        """Use semantic search to find matching FOAs for a researcher's query."""
        # Using the semantic search capabilities of the FOAStore (ChromaDB)
        return self.foa_store.search_semantic(query=profile.query, limit=limit)

    def generate_digest(self, profile: ResearcherProfile) -> str:
        """Generate a mock email digest of matching opportunities."""
        matches = self.get_matches_for_profile(profile)
        
        lines = [
            f"Subject: New Funding Opportunities matching '{profile.query}'",
            f"To: {profile.email}",
            f"Hello {profile.name},",
            "",
            "Here are the latest funding opportunities matching your research profile:",
            "-" * 60
        ]
        
        if not matches:
            lines.append("No matches found at this time.")
        else:
            for m in matches:
                lines.append(f"Title:  {m.title}")
                lines.append(f"Agency: {m.agency}")
                lines.append(f"URL:    {m.url}")
                lines.append("-" * 60)
                
        digest = "\n".join(lines)
        logger.info(f"\n[MOCK EMAIL SENT]\n{digest}\n")
        return digest
