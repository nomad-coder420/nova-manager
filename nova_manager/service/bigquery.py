import pandas as pd
import json

from google.cloud import bigquery

from nova_manager.core.config import GCP_PROJECT_ID, BIGQUERY_LOCATION

bq_client = bigquery.Client(project=GCP_PROJECT_ID)


class BigQueryService:
    def insert_rows(self, table_name: str, rows: list[dict]):
        bq_client.insert_rows_json(table_name, rows)

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
        partition_field: str = None,
        clustering_fields: list[str] = None,
    ):
        from google.api_core.exceptions import NotFound
        from google.cloud import bigquery

        print(f"Checking table {table_name}")
        try:
            table = bq_client.get_table(table_name)
            print(f"Table {table_name} already exists: {table}")
            return  # Table exists
        except NotFound:
            pass  # Table does not exist, proceed to create

        table = bigquery.Table(
            table_name,
            schema=[
                bigquery.SchemaField(field["name"], field["type"]) for field in schema
            ],
        )

        if partition_field:
            table.time_partitioning = bigquery.TimePartitioning(field=partition_field)

        if clustering_fields:
            table.clustering_fields = clustering_fields

        print(f"Creating table {table_name}")
        bq_client.create_table(table)
        print(f"Table {table_name} created")
