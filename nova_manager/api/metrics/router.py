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
from nova_manager.database.session import get_db
from nova_manager.service.bigquery import BigQueryService
from nova_manager.queues.controller import QueueController
from nova_manager.components.auth.dependencies import (
    require_app_context,
    require_sdk_app_context,
)
from nova_manager.core.security import AuthContext, SDKAuthContext
from sqlalchemy.orm import Session


router = APIRouter()


@router.post("/track-event/")
async def track_event(
    event: TrackEventRequest, auth: SDKAuthContext = Depends(require_sdk_app_context)
):
    # Enqueue background job using organisation/app from API key
    QueueController().add_task(
        EventsController(auth.organisation_id, auth.app_id).track_event,
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
):
    organisation_id = auth.organisation_id
    app_id = auth.app_id
    type = compute_request.type
    config = compute_request.config

    # extract personalisation_ids array and move first value into filters
    personalisation_ids = config.pop("personalisation_ids", None)
    if personalisation_ids:
        # take the first id and add as user_experience filter
        first_id = personalisation_ids[0]
        filters = config.setdefault("filters", {})
        filters["personalisation_id"] = {
            "value": first_id,
            "source": "user_experience",
            "op": "=",
        }

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
