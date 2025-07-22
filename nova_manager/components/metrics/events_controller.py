from datetime import datetime, timezone
import json
from typing import TypedDict
from uuid import UUID
import uuid


from nova_manager.components.metrics.artefacts import EventsArtefacts
from nova_manager.components.user_experience.models import UserExperience
from nova_manager.components.users.models import Users
from nova_manager.core.config import (
    BIGQUERY_DATASET_NAME,
    BIGQUERY_RAW_EVENTS_TABLE_NAME,
    GCP_PROJECT_ID,
)
from nova_manager.core.log import logger

from datetime import datetime
from uuid import UUID

from nova_manager.service.bigquery import BigQueryService


class TrackEvent(TypedDict):
    event_name: str
    event_data: dict | None = None


class EventsController(EventsArtefacts):
    def track_events(
        self,
        user_id: UUID,
        timestamp: datetime,
        events: list[TrackEvent],
    ):
        time_now = datetime.now(timezone.utc)

        raw_events_rows = []
        event_table_rows = {}
        event_props_table_rows = {}

        bigquery_table_name = (
            f"{GCP_PROJECT_ID}.{BIGQUERY_DATASET_NAME}.{BIGQUERY_RAW_EVENTS_TABLE_NAME}"
        )

        for event in events:
            event_id = str(uuid.uuid4())
            event_name = event["event_name"]
            event_data = event["event_data"] or {}

            raw_events_rows.append(
                {
                    "event_id": event_id,
                    "user_id": str(user_id),
                    "org_id": str(self.organisation_id),
                    "app_id": str(self.app_id),
                    "client_ts": timestamp.isoformat(),
                    "server_ts": time_now.isoformat(),
                    "event_name": event_name,
                    "event_data": json.dumps(event_data),
                }
            )

            # TODO: Create table if not exists

            event_table_name = self._event_table_name(event_name)
            event_props_table_name = self._event_props_table_name(event_name)

            event_table_rows[event_table_name] = {
                "event_id": event_id,
                "user_id": str(user_id),
                "org_id": str(self.organisation_id),
                "app_id": str(self.app_id),
                "event_name": event_name,
                "client_ts": timestamp.isoformat(),
                "server_ts": time_now.isoformat(),
            }

            event_props_table_rows[event_props_table_name] = [
                {
                    "event_id": event_id,
                    "user_id": str(user_id),
                    "org_id": str(self.organisation_id),
                    "app_id": str(self.app_id),
                    "event_name": event_name,
                    "key": key,
                    "value": event_data[key],
                    "client_ts": timestamp.isoformat(),
                    "server_ts": time_now.isoformat(),
                }
                for key in event_data
            ]

        try:
            errors = BigQueryService().insert_rows(bigquery_table_name, raw_events_rows)

            if errors:
                raise Exception(str(errors))

            for table_name, row in event_table_rows.items():
                errors = BigQueryService().insert_rows(table_name, [row])
                if errors:
                    raise Exception(str(errors))

            for table_name, rows in event_props_table_rows.items():
                errors = BigQueryService().insert_rows(table_name, rows)
                if errors:
                    raise Exception(str(errors))

        except Exception as e:
            logger.error(f"BigQuery insertion failed: {str(e)}")
            raise e

    def track_event(
        self,
        user_id: UUID,
        timestamp: datetime,
        event_name: str,
        event_data: dict | None = None,
    ):
        if not event_data:
            event_data = {}

        return self.track_events(
            user_id, timestamp, [{"event_name": event_name, "event_data": event_data}]
        )

    def track_user_experience(self, user_experience: UserExperience):
        user_experience_table_name = ""

        user_experience_row = {
            "user_id": str(user_experience.user_id),
            "org_id": str(user_experience.organisation_id),
            "app_id": str(user_experience.app_id),
            "experience_id": str(user_experience.experience_id),
            "personalisation_id": str(user_experience.personalisation_id),
            "personalisation_name": user_experience.personalisation_name,
            "feature_variants": json.dumps(user_experience.feature_variants),
            "evaluation_reason": user_experience.evaluation_reason,
            "assigned_at": user_experience.assigned_at.isoformat(),
        }

        BigQueryService.insert_rows(user_experience_table_name, [user_experience_row])

    def track_user_profile(self, user: Users):
        user_profile_table_name = ""

        user_profile_rows = [
            {
                "user_id": str(user.pid),
                "org_id": str(user.organisation_id),
                "app_id": str(user.app_id),
                "key": key,
                "value": user.user_profile[key],
            }
            for key in user.user_profile
        ]

        BigQueryService.insert_rows(user_profile_table_name, user_profile_rows)
