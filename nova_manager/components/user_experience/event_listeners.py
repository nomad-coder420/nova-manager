from sqlalchemy import event

from nova_manager.components.user_experience.models import UserExperience
from nova_manager.components.metrics.events_controller import EventsController


@event.listens_for(UserExperience, "after_insert")
def after_insert(mapper, connection, target: UserExperience):
    EventsController().track_user_experience(target)
