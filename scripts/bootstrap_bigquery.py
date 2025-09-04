#!/usr/bin/env python
"""
Idempotent script to create BigQuery datasets and tables for all existing apps and events.
Usage:
  poetry run python scripts/bootstrap_bigquery.py
"""
import sys
from typing import List, Tuple
import logging

from nova_manager.database.session import SessionLocal
from nova_manager.components.metrics.models import EventsSchema
from nova_manager.components.auth.models import App as AuthApp
from nova_manager.components.metrics.artefacts import EventsArtefacts
from nova_manager.service.bigquery import BigQueryService
from nova_manager.core.config import GCP_PROJECT_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    bq_service = BigQueryService()
    # Open a database session
    db = SessionLocal()
    try:
        # find all (organisation_id, app_id) combinations from Apps table
        apps: List[Tuple[str, str]] = (
            db.query(AuthApp.organisation_id, AuthApp.pid)
              .distinct()
              .all()
        )
        if not apps:
            logger.info("No apps found. Exiting.")
            return

        for organisation_id, app_id in apps:
            str_org = str(organisation_id)
            str_app = str(app_id)
            logger.info(f"Bootstrapping BQ for org={str_org}, app={str_app}")
            artefacts = EventsArtefacts(str_org, str_app)
            full_dataset = f"{GCP_PROJECT_ID}.{artefacts.dataset_name}"

            # create dataset
            bq_service.create_dataset_if_not_exists(full_dataset)

            # default tables: raw_events, user_experience, user_profile_props
            # raw_events
            # use full project.dataset.table name
            raw_table = f"{GCP_PROJECT_ID}.{artefacts._raw_events_table_name()}"
            bq_service.create_table_if_not_exists(raw_table, schema=[
                {'name': 'event_id', 'type': 'STRING'},
                {'name': 'user_id', 'type': 'STRING'},
                {'name': 'client_ts', 'type': 'TIMESTAMP'},
                {'name': 'server_ts', 'type': 'TIMESTAMP'},
                {'name': 'event_name', 'type': 'STRING'},
                {'name': 'event_data', 'type': 'STRING'},
            ])

            # user_experience
            ue_table = f"{GCP_PROJECT_ID}.{artefacts._user_experience_table_name()}"
            bq_service.create_table_if_not_exists(ue_table, schema=[
                {'name': 'user_id', 'type': 'STRING'},
                {'name': 'experience_id', 'type': 'STRING'},
                {'name': 'personalisation_id', 'type': 'STRING'},
                {'name': 'personalisation_name', 'type': 'STRING'},
                {'name': 'experience_variant_id', 'type': 'STRING'},
                {'name': 'features', 'type': 'STRING'},
                {'name': 'evaluation_reason', 'type': 'STRING'},
                {'name': 'assigned_at', 'type': 'TIMESTAMP'},
            ])

            # user_profile_props
            up_table = f"{GCP_PROJECT_ID}.{artefacts._user_profile_props_table_name()}"
            bq_service.create_table_if_not_exists(
                up_table,
                schema=[
                    {'name': 'user_id', 'type': 'STRING'},
                    {'name': 'key', 'type': 'STRING'},
                    {'name': 'value', 'type': 'STRING'},
                    {'name': 'server_ts', 'type': 'TIMESTAMP'},
                ],
                partition_field='server_ts',
                clustering_fields=['user_id', 'key'],
            )

            # create tables for each event and props
            # filter using string IDs to match String columns in EventsSchema
            event_schemas = db.query(EventsSchema).filter_by(
                organisation_id=str_org,
                app_id=str_app
            ).all()

            for es in event_schemas:
                event_name = es.event_name
                # event table
                evt_table_id = f"{GCP_PROJECT_ID}.{artefacts._event_table_name(event_name)}"
                bq_service.create_table_if_not_exists(
                    evt_table_id,
                    schema=[
                        {'name': 'event_id', 'type': 'STRING'},
                        {'name': 'user_id', 'type': 'STRING'},
                        {'name': 'event_name', 'type': 'STRING'},
                        {'name': 'client_ts', 'type': 'TIMESTAMP'},
                        {'name': 'server_ts', 'type': 'TIMESTAMP'},
                    ],
                    partition_field='client_ts',
                    clustering_fields=['event_name', 'user_id'],
                )

                # props table
                props_table_id = f"{GCP_PROJECT_ID}.{artefacts._event_props_table_name(event_name)}"
                bq_service.create_table_if_not_exists(
                    props_table_id,
                    schema=[
                        {'name': 'event_id', 'type': 'STRING'},
                        {'name': 'user_id', 'type': 'STRING'},
                        {'name': 'event_name', 'type': 'STRING'},
                        {'name': 'key', 'type': 'STRING'},
                        {'name': 'value', 'type': 'STRING'},
                        {'name': 'client_ts', 'type': 'TIMESTAMP'},
                        {'name': 'server_ts', 'type': 'TIMESTAMP'},
                    ],
                    partition_field='client_ts',
                    clustering_fields=['event_name', 'user_id'],
                )
    finally:
        db.close()
        db.close()
    logger.info("BigQuery bootstrap complete.")

if __name__ == '__main__':
    sys.exit(main())
