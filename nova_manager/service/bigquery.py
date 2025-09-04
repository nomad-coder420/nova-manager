import pandas as pd
import json

from google.cloud import bigquery
from google.api_core.exceptions import NotFound

from nova_manager.core.config import GCP_PROJECT_ID, BIGQUERY_LOCATION
from nova_manager.core.log import logger


bq_client = bigquery.Client(project=GCP_PROJECT_ID)


class BigQueryService:
    def insert_rows(self, table_name: str, rows: list[dict]):
        errors = bq_client.insert_rows_json(table_name, rows)
        return errors

    def run_query(self, query: str):
        query_job = bq_client.query(query, location=BIGQUERY_LOCATION)
        rows = query_job.result()

        result_df: pd.DataFrame = rows.to_dataframe()

        result_json = result_df.to_json(orient="records")

        if result_json:
            return json.loads(result_json)

        return []

    def create_table_if_not_exists(
        self,
        table_name: str,
        schema: list[dict],
        partition_field: str | None = None,
        clustering_fields: list[str] | None = None,
    ):
        try:
            table = bq_client.get_table(table_name)
            logger.info(f"Table already exists: {table_name}")
            return  # Table exists
        except NotFound:
            logger.info(f"Table not found, will create: {table_name}")
        except Exception as e:
            logger.error(f"Error checking if table exists {table_name}: {str(e)}")
            raise e

        # Build and create new table
        try:
            table = bigquery.Table(
                table_name,
                schema=[
                    bigquery.SchemaField(field["name"], field["type"])
                    for field in schema
                ],
            )

            if partition_field:
                table.time_partitioning = bigquery.TimePartitioning(
                    field=partition_field
                )

            if clustering_fields:
                table.clustering_fields = clustering_fields

            logger.info(f"Creating table {table_name}")

            bq_client.create_table(table)
            logger.info(f"Table created: {table_name}")
        except Exception as e:
            logger.error(f"Error creating table {table_name}: {str(e)}")
            raise e

    def create_dataset_if_not_exists(
        self, dataset_name: str, location: str = BIGQUERY_LOCATION
    ):
        try:
            logger.info(f"Checking if dataset exists: {dataset_name}")

            bq_client.get_dataset(dataset_name)
            logger.info(f"Dataset already exists: {dataset_name}")

            return
        except NotFound:
            logger.info(f"Dataset not found, creating: {dataset_name}")
        except Exception as e:
            logger.error(f"Error checking dataset {dataset_name}: {str(e)}")
            raise e

        try:
            dataset = bigquery.Dataset(dataset_name)
            dataset.location = location

            bq_client.create_dataset(dataset)
            logger.info(f"Dataset created successfully: {dataset_name}")
        except Exception as e:
            logger.error(f"Error creating dataset {dataset_name}: {str(e)}")
            raise e
