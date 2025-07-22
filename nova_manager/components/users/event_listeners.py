from sqlalchemy import event

from nova_manager.components.metrics.events_controller import EventsController
from nova_manager.components.users.models import Users


@event.listens_for(Users, "after_insert")
def after_insert(mapper, connection, target: Users):
    EventsController().track_user_profile(target)
