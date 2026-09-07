from app.schemas.models import CareEvent, ContextState, KnowledgeItem


class KnowledgeRetriever:
    def retrieve(self, context: ContextState, event: CareEvent, limit: int = 3) -> list[KnowledgeItem]:
        terms = " ".join([event.type, event.source, str(event.data)]).lower()
        selected = [item for item in context.knowledge_base if any(tag.lower() in terms for tag in item.tags)]
        if not selected and event.type == "conversation":
            selected = [item for item in context.knowledge_base if "companion" in item.tags]
        return selected[:limit]

