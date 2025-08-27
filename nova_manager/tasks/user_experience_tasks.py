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
    
    This also handles the special case where users have NULL personalisation_id with
    specific evaluation reasons that should be invalidated when a personalisation
    is re-enabled.
    """
    from nova_manager.components.personalisations.models import Personalisations
    
    with db_session() as db:
        # First, get the experience_id for this personalisation
        personalisation = db.query(Personalisations).filter(
            Personalisations.pid == personalisation_id
        ).first()
        
        if not personalisation:
            logger.error(f"Cannot find personalisation with ID {personalisation_id}")
            return
            
        experience_id = personalisation.experience_id
        
        # Define evaluation reasons that should be invalidated
        invalid_evaluation_reasons = [
            "default_experience",
            "no_personalisation_match_error", 
            "no_experience_assignment_error"
        ]
        
        # 1. Delete records with matching personalisation_id (regular case)
        deleted_direct = (
            db.query(UserExperience)
            .filter(
                UserExperience.personalisation_id == personalisation_id,
                UserExperience.organisation_id == organisation_id,
                UserExperience.app_id == app_id,
            )
            .delete(synchronize_session=False)
        )
        
        # 2. Delete records with NULL personalisation_id but with invalid evaluation reasons
        # and for the same experience
        deleted_null_personalisation = (
            db.query(UserExperience)
            .filter(
                UserExperience.personalisation_id.is_(None),
                UserExperience.organisation_id == organisation_id,
                UserExperience.app_id == app_id,
                UserExperience.experience_id == experience_id,
                UserExperience.evaluation_reason.in_(invalid_evaluation_reasons)
            )
            .delete(synchronize_session=False)
        )
        
        total_deleted = deleted_direct + deleted_null_personalisation
        
        logger.info(
            f"Background task: deleted {total_deleted} assignments for personalisation {personalisation_id} "
            f"({deleted_direct} direct, {deleted_null_personalisation} with null personalisation_id)"
        )
