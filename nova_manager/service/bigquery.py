import pandas as pd
import json

from google.cloud import bigquery
from google.api_core.exceptions import NotFound, GoogleAPIError
from nova_manager.core.log import logger
import re

from nova_manager.core.config import GCP_PROJECT_ID, BIGQUERY_LOCATION

try:
    logger.info(f"Initializing BigQuery client with project ID: {GCP_PROJECT_ID}")
    bq_client = bigquery.Client(project=GCP_PROJECT_ID)
    logger.info("BigQuery client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize BigQuery client: {str(e)}")
    raise


class BigQueryService:
    def insert_rows(self, table_name: str, rows: list[dict]):
        logger.info(f"BigQueryService.insert_rows: inserting {len(rows)} rows into {table_name}")
        try:
            errors = bq_client.insert_rows_json(table_name, rows)
            if errors:
                logger.error(f"Error inserting rows into {table_name}: {errors}")
            return errors
        except Exception as e:
            logger.error(f"Exception inserting rows into {table_name}: {str(e)}")
            raise e

    def run_query(self, query: str):
        logger.info(f"BigQueryService.run_query: executing query: {query}")
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
        partition_field: str = None,
        clustering_fields: list[str] = None,
    ):
        # Ensure dataset and table identifiers are BigQuery-safe
        from google.api_core.exceptions import NotFound
        from google.cloud import bigquery

        parts = table_name.split('.')
        project = parts[0]
        raw_dataset = parts[1]
        raw_table = parts[2]
        safe_dataset = re.sub(r'[^a-zA-Z0-9_]', '_', raw_dataset)
        safe_table = re.sub(r'[^a-zA-Z0-9_]', '_', raw_table)
        safe_full_name = f"{project}.{safe_dataset}.{safe_table}"

        logger.info(f"BigQueryService.create_table_if_not_exists: checking table {safe_full_name}")
        
        # First, try to create dataset if it doesn't exist
        try:
            dataset_id = f"{project}.{safe_dataset}"
            self.create_dataset_if_not_exists(dataset_id)
        except Exception as e:
            logger.error(f"Error creating dataset for table {safe_full_name}: {str(e)}")
            raise e
            
        try:
            existing = bq_client.get_table(safe_full_name)
            logger.info(f"Table already exists: {safe_full_name}")
            return
        except NotFound:
            logger.info(f"Table not found, will create: {safe_full_name}")
        except Exception as e:
            logger.error(f"Error checking if table exists {safe_full_name}: {str(e)}")
            raise e

        # Build and create new table
        try:
            table = bigquery.Table(
                safe_full_name,
                schema=[bigquery.SchemaField(field['name'], field['type']) for field in schema],
            )
            if partition_field:
                table.time_partitioning = bigquery.TimePartitioning(field=partition_field)
            if clustering_fields:
                table.clustering_fields = clustering_fields

            logger.info(f"Creating table {safe_full_name}")
            bq_client.create_table(table)
            logger.info(f"Table created: {safe_full_name}")
        except Exception as e:
            logger.error(f"Error creating table {safe_full_name}: {str(e)}")
            raise e
    
    def create_dataset_if_not_exists(self, dataset_name: str, location: str = BIGQUERY_LOCATION):
        # Ensure dataset ID is alphanumeric+underscores
        parts = dataset_name.split('.')
        project = parts[0]
        raw_ds = parts[-1]
        safe_ds = re.sub(r'[^a-zA-Z0-9_]', '_', raw_ds)
        full_name = f"{project}.{safe_ds}"
        try:
            logger.info(f"Checking if dataset exists: {full_name}")
            bq_client.get_dataset(full_name)
            logger.info(f"Dataset already exists: {full_name}")
        except NotFound:
            logger.info(f"Dataset not found, creating: {full_name}")
            ds = bigquery.Dataset(full_name)
            ds.location = location
            try:
                bq_client.create_dataset(ds)
                logger.info(f"Dataset created successfully: {full_name}")
            except Exception as e:
                logger.error(f"Error creating dataset {full_name}: {str(e)}")
                raise e
        except Exception as e:
            logger.error(f"Error checking dataset {full_name}: {str(e)}")
            raise e
