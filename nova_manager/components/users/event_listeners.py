from sqlalchemy import event

from nova_manager.components.metrics.events_controller import EventsController
from nova_manager.components.users.models import Users
from nova_manager.queues.controller import QueueController


@event.listens_for(Users, "after_update")
@event.listens_for(Users, "after_insert")
def after_insert(mapper, connection, target: Users):
    QueueController().add_task(
        EventsController().track_user_profile,
        target,
    )
