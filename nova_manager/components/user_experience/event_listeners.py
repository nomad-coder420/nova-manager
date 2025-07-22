from sqlalchemy import event

from nova_manager.components.user_experience.models import UserExperience
from nova_manager.components.metrics.events_controller import EventsController
from nova_manager.queues.controller import QueueController


@event.listens_for(UserExperience, "after_insert")
def after_insert(mapper, connection, target: UserExperience):
    QueueController().add_task(
        EventsController().track_user_experience,
        target,
    )
