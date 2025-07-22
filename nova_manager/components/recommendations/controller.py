from nova_manager.components.recommendations.schemas import RecommendationSchema


class RecommendationsController:
    def get_recommendations(
        self, user_prompt: str, experiences_context
    ) -> list[RecommendationSchema]:
        return []
