from nova_manager.database.session import db_session
from nova_manager.components.user_experience.models import UserExperience
import logging

logger = logging.getLogger(__name__)


def delete_personalisation_assignments(
    personalisation_id: str,
    organisation_id: str,
    app_id: str,
) -> None:
    """
    RQ task to delete existing UserExperience assignments for a given personalisation.
    """
    with db_session() as db:
        deleted = (
            db.query(UserExperience)
            .filter(
                UserExperience.personalisation_id == personalisation_id,
                UserExperience.organisation_id == organisation_id,
                UserExperience.app_id == app_id,
            )
            .delete(synchronize_session=False)
        )
        logger.info(
            f"Background task: deleted {deleted} assignments for personalisation {personalisation_id}"
        )
