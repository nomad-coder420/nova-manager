import pandas as pd
import json

from google.cloud import bigquery

from nova_manager.core.config import GCP_PROJECT_ID

bq_client = bigquery.Client(project=GCP_PROJECT_ID)


class BigQueryService:
    def insert_rows(self, table_name: str, rows: list[dict]):
        bq_client.insert_rows_json(table_name, rows)

    def run_query(self, query: str):
        query_job = bq_client.query(query)
        rows = query_job.result()

        result_df: pd.DataFrame = rows.to_dataframe()

        result_json = result_df.to_json(orient="records")

        if result_json:
            return json.loads(result_json)

        return []
