from typing import Dict, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from nova_manager.api.metrics.request_response import (
    CreateMetricRequest,
    ComputeMetricRequest,
    EventsSchemaResponse,
    MetricResponse,
    TrackEventRequest,
    UserProfileKeyResponse,
)
from nova_manager.components.metrics.crud import (
    MetricsCRUD,
    EventsSchemaCRUD,
    UserProfileKeysCRUD,
)
from nova_manager.components.metrics.events_controller import EventsController
from nova_manager.components.metrics.query_builder import QueryBuilder
from nova_manager.components.segments.crud import SegmentsCRUD
from nova_manager.components.metrics.query_builder import KeySource
from nova_manager.database.session import get_db
from nova_manager.service.bigquery import BigQueryService
from nova_manager.queues.controller import QueueController
from nova_manager.components.auth.dependencies import require_app_context
from nova_manager.core.security import AuthContext
from sqlalchemy.orm import Session


router = APIRouter()


@router.post("/track-event/")
async def track_event(event: TrackEventRequest):
    QueueController().add_task(
        EventsController(event.organisation_id, event.app_id).track_event,
        event.user_id,
        event.event_name,
        event.event_data,
        event.timestamp,
    )

    return {"success": True}


@router.post("/compute/", response_model=List[Dict])
async def compute_metric(
    compute_request: ComputeMetricRequest,
    auth: AuthContext = Depends(require_app_context),
    db: Session = Depends(get_db),
):
    organisation_id = auth.organisation_id
    app_id = auth.app_id
    type = compute_request.type
    # copy config and extract any segment filters
    config = compute_request.config.copy()
    # allow passing segment_ids list or single segment_id inside config
    segment_ids = None
    if "segment_ids" in config:
        segment_ids = config.pop("segment_ids") or []
    elif "segment_id" in config:
        segment_ids = [config.pop("segment_id")]
    # merge each segment's conditions into filters
    if segment_ids:
        filters = config.get("filters", {})
        op_map = {"equals": "=", "not_equals": "!=", "gt": ">", "lt": "<", "gte": ">=", "lte": "<="}
        for sid in segment_ids:
            segment = SegmentsCRUD(db).get_by_pid(sid)
            if not segment:
                raise HTTPException(status_code=404, detail=f"Segment {sid} not found")
            for cond in segment.rule_config.get("conditions", []):
                key = cond["field"]
                op = op_map.get(cond["operator"], "=")
                filters[key] = {
                    "value": cond.get("value"),
                    "op": op,
                    "source": KeySource.USER_PROFILE,
                }
        config["filters"] = filters

    query_builder = QueryBuilder(organisation_id, app_id)
    query = query_builder.build_query(type, config)

    big_query_service = BigQueryService()
    result = big_query_service.run_query(query)

    return result


@router.get("/events-schema/", response_model=List[EventsSchemaResponse])
async def list_events_schema(
    auth: AuthContext = Depends(require_app_context),
    search: str = Query(None),
    db: Session = Depends(get_db),
):
    """Get all events schema for an organization/app with optional search"""
    events_schema_crud = EventsSchemaCRUD(db)

    if search:
        events_schema = events_schema_crud.search_events_schema(
            organisation_id=str(auth.organisation_id),
            app_id=auth.app_id,
            search_term=search,
            skip=0,
            limit=100,
        )
    else:
        events_schema = events_schema_crud.get_multi_by_org(
            organisation_id=str(auth.organisation_id),
            app_id=auth.app_id,
            skip=0,
            limit=100,
        )

    return events_schema


@router.get("/user-profile-keys/", response_model=List[UserProfileKeyResponse])
async def list_user_profile_keys(
    auth: AuthContext = Depends(require_app_context),
    search: str = Query(None),
    db: Session = Depends(get_db),
):
    """Get all user profile keys for an organization/app with optional search"""
    user_profile_keys_crud = UserProfileKeysCRUD(db)

    if search:
        user_profile_keys = user_profile_keys_crud.search_user_profile_keys(
            organisation_id=auth.organisation_id,
            app_id=auth.app_id,
            search_term=search,
            skip=0,
            limit=100,
        )
    else:
        user_profile_keys = user_profile_keys_crud.get_multi_by_org(
            organisation_id=auth.organisation_id,
            app_id=auth.app_id,
            skip=0,
            limit=100,
        )

    return user_profile_keys


@router.post("/")
async def create_metric(
    metric_data: CreateMetricRequest,
    auth: AuthContext = Depends(require_app_context),
    db: Session = Depends(get_db),
):
    metrics_crud = MetricsCRUD(db)

    organisation_id = str(auth.organisation_id)
    app_id = auth.app_id
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
    auth: AuthContext = Depends(require_app_context),
    db: Session = Depends(get_db),
):
    metrics_crud = MetricsCRUD(db)

    metrics = metrics_crud.get_multi(
        organisation_id=auth.organisation_id, app_id=auth.app_id
    )

    return metrics


@router.get("/{metric_id}/", response_model=MetricResponse)
async def get_metric(
    metric_id: UUID,
    auth: AuthContext = Depends(require_app_context),
    db: Session = Depends(get_db),
):
    metrics_crud = MetricsCRUD(db)

    metric = metrics_crud.get_by_pid(metric_id)

    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    return metric


@router.put("/{metric_id}/", response_model=MetricResponse)
async def update_metric(
    metric_id: UUID,
    metric_data: CreateMetricRequest,
    auth: AuthContext = Depends(require_app_context),
    db: Session = Depends(get_db),
):
    metrics_crud = MetricsCRUD(db)

    # Check if metric exists
    existing_metric = metrics_crud.get_by_pid(metric_id)
    if not existing_metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    # Update the metric
    update_data = {
        "name": metric_data.name,
        "description": metric_data.description,
        "type": metric_data.type,
        "config": metric_data.config,
    }

    updated_metric = metrics_crud.update(existing_metric.id, update_data)

    return updated_metric
