from typing import List, Optional

from sqlmodel import Session, select

from core.database.entities import ResearcherEntity
from core.database.session import engine
from core.models import ResearcherCreate, ResearcherProfile


class ResearcherStore:
    """Store for managing researcher profiles."""

    def create(self, data: ResearcherCreate) -> ResearcherProfile:
        with Session(engine) as session:
            entity = ResearcherEntity(**data.model_dump())
            session.add(entity)
            session.commit()
            session.refresh(entity)
            return self._entity_to_model(entity)

    def get_all(self) -> List[ResearcherProfile]:
        with Session(engine) as session:
            statement = select(ResearcherEntity)
            entities = session.exec(statement).all()
            return [self._entity_to_model(e) for e in entities]

    def get(self, profile_id: int) -> Optional[ResearcherProfile]:
        with Session(engine) as session:
            entity = session.get(ResearcherEntity, profile_id)
            if entity:
                return self._entity_to_model(entity)
            return None

    def _entity_to_model(self, entity: ResearcherEntity) -> ResearcherProfile:
        return ResearcherProfile(
            id=entity.id,
            name=entity.name,
            email=entity.email,
            query=entity.query,
            match_threshold=entity.match_threshold,
        )
