from datetime import datetime, timezone
import json
from typing import TypedDict
from uuid import UUID
import uuid

from google.cloud import bigquery

from nova_manager.core.config import (
    BIGQUERY_DATASET_NAME,
    BIGQUERY_RAW_EVENTS_TABLE_NAME,
    GCP_PROJECT_ID,
)
from nova_manager.core.log import logger

bq_client = bigquery.Client(project=GCP_PROJECT_ID)


class TrackEvent(TypedDict):
    event_name: str
    event_data: dict | None


class BigQueryService:
    def track_events(
        self,
        user_id: UUID,
        organisation_id: str,
        app_id: str,
        timestamp: datetime,
        events: list[TrackEvent],
    ):
        time_now = datetime.now(timezone.utc)

        rows = []

        bigquery_table_name = (
            f"{GCP_PROJECT_ID}.{BIGQUERY_DATASET_NAME}.{BIGQUERY_RAW_EVENTS_TABLE_NAME}"
        )

        for event in events:
            rows.append(
                {
                    "event_id": str(uuid.uuid4()),
                    "user_id": str(user_id),
                    "org_id": str(organisation_id),
                    "app_id": str(app_id),
                    "client_ts": timestamp.isoformat(),
                    "server_ts": time_now.isoformat(),
                    "event_name": event["event_name"],
                    "event_data": json.dumps(event["event_data"] or {}),
                }
            )

        try:
            errors = bq_client.insert_rows_json(bigquery_table_name, rows)

            if errors:
                raise Exception(str(errors))

        except Exception as e:
            logger.error(f"BigQuery insertion failed: {str(e)}")
            raise e

    def track_event(
        self,
        user_id: UUID,
        organisation_id: str,
        app_id: str,
        timestamp: datetime,
        event_name: str,
        event_data: dict | None,
    ):
        if not event_data:
            event_data = {}

        return self.track_events(
            user_id,
            organisation_id,
            app_id,
            timestamp,
            [{"event_name": event_name, "event_data": event_data}],
        )

    def run_query(self, query: str, organisation_id: str, app_id: str):
        query_job = bq_client.query(query)
        rows = query_job.result()

        # Convert to list of dictionaries for API responses
        results = []
        for row in rows:
            results.append(dict(row))

        # print(rows.to_dataframe())

        return results
