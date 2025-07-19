from datetime import datetime
from typing import Dict, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from nova_manager.api.metrics.request_response import (
    CreateMetricRequest,
    ComputeMetricRequest,
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


@router.post("/compute/", response_model=List[Dict])
async def compute_metric(compute_request: ComputeMetricRequest):
    organisation_id = compute_request.organisation_id
    app_id = compute_request.app_id
    type = compute_request.type
    config = compute_request.config

    query_builder = QueryBuilder(organisation_id, app_id)
    query = query_builder.build_query(type, config)

    big_query_service = BigQueryService()
    result = big_query_service.run_query(query)

    return result


@router.post("/")
async def create_metric(
    metric_data: CreateMetricRequest, db: Session = Depends(get_db)
):
    metrics_crud = MetricsCRUD(db)

    organisation_id = metric_data.organisation_id
    app_id = metric_data.app_id
    name = metric_data.name
    description = metric_data.description
    type = metric_data.type
    config = metric_data.config

    metric = metrics_crud.create(
        {
            "organisation_id": organisation_id,
            "app_id": app_id,
            "name": name,
            "description": description,
            "type": type,
            "config": config,
        }
    )

    return metric


@router.get("/", response_model=List[MetricResponse])
async def list_metric(
    organisation_id: str = Query(...),
    app_id: str = Query(...),
    db: Session = Depends(get_db),
):
    metrics_crud = MetricsCRUD(db)

    metrics = metrics_crud.get_multi(organisation_id=organisation_id, app_id=app_id)

    return metrics


@router.get("/{metric_id}/", response_model=MetricResponse)
async def get_metric(metric_id: UUID, db: Session = Depends(get_db)):
    metrics_crud = MetricsCRUD(db)

    metric = metrics_crud.get_by_pid(metric_id)

    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    return metric
