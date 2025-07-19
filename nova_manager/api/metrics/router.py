from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from nova_manager.api.metrics.request_response import (
    CreateMetricRequest,
    MetricResponse,
    TrackEventRequest,
)
from nova_manager.components.metrics.crud import MetricsCRUD
from nova_manager.components.metrics.query_builder import QueryBuilder
from nova_manager.database.session import get_db
from nova_manager.service.bigquery import BigQueryService
from sqlalchemy.orm import Session


router = APIRouter()


@router.post("/track-event/")
async def track_event(event: TrackEventRequest):
    BigQueryService().track_event(
        event.user_id,
        event.organisation_id,
        event.app_id,
        event.timestamp,
        event.event_name,
        event.event_data,
    )

    return {"success": True}


@router.get("/{metric_id}/evaluate/", response_model=list[dict])
async def evaluate_metric(metric_id: UUID, db: Session = Depends(get_db)):
    metrics_crud = MetricsCRUD(db)
    big_query_service = BigQueryService()

    metric = metrics_crud.get_by_pid(metric_id)

    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    query = metric.query
    organisation_id = metric.organisation_id
    app_id = metric.app_id

    result = big_query_service.run_query(query, organisation_id, app_id)

    return result


@router.post("/")
async def create_metric(
    metric_data: CreateMetricRequest, db: Session = Depends(get_db)
):
    organisation_id = metric_data.organisation_id
    app_id = metric_data.app_id

    query_builder = QueryBuilder(organisation_id, app_id)
    metrics_crud = MetricsCRUD(db)

    name = metric_data.name
    description = metric_data.description
    type = metric_data.type
    config = metric_data.config

    query = query_builder.build_query(name, type, config)

    metric = metrics_crud.create(
        {
            "organisation_id": organisation_id,
            "app_id": app_id,
            "name": name,
            "description": description,
            "type": type,
            "config": config,
            "query": query,
        }
    )


@router.get("/", response_model=list[MetricResponse])
async def list_metric(
    organisation_id: str = Query(...),
    app_id: str = Query(...),
    db: Session = Depends(get_db),
):
    metrics_crud = MetricsCRUD(db)

    metrics = metrics_crud.get_multi(organisation_id=organisation_id, app_id=app_id)

    return metrics
