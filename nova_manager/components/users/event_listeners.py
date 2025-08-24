from sqlalchemy import event

from nova_manager.components.metrics.events_controller import EventsController
from nova_manager.components.users.models import Users
from nova_manager.queues.controller import QueueController
from nova_manager.core.log import logger


@event.listens_for(Users, "after_update")
@event.listens_for(Users, "after_insert")
def after_insert(mapper, connection, target: Users):
    logger.info(f"User event listener triggered: user_id={target.pid}, org={target.organisation_id}, app={target.app_id}")
    job_id = QueueController().add_task(
        EventsController(target.organisation_id, target.app_id).track_user_profile,
        target,
    )
    logger.info(f"Queued track_user_profile task with ID: {job_id}")
