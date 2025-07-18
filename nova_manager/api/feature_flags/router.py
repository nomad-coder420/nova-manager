import traceback
from typing import Dict, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from nova_manager.components.auth.dependencies import RoleRequired
from nova_manager.components.auth.enums import AppRole
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError


from nova_manager.api.feature_flags.request_response import (
    FeatureFlagCreate,
    FeatureFlagListItem,
    FeatureFlagResponse,
    FeatureFlagDetailedResponse,
    FeatureFlagUpdate,
    IndividualTargetingCreate,
    NovaObjectSyncRequest,
    NovaObjectSyncResponse,
    TargetingRuleCreate,
    VariantCreate,
    VariantResponse,
)
from nova_manager.components.feature_flags.crud import (
    FeatureFlagsCRUD,
    FeatureVariantsCRUD,
)
from nova_manager.database.session import get_db
from fastapi import Depends
from nova_manager.components.auth.dependencies import RoleRequired
from nova_manager.components.auth.enums import AppRole


router = APIRouter()


@router.post(
    "/sync-nova-objects/",
    dependencies=[Depends(RoleRequired([
        AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def sync_nova_objects(
    sync_request: NovaObjectSyncRequest, db: Session = Depends(get_db)
):
    """
    Sync Nova objects from client application to create/update feature flags

    This endpoint:
    1. Takes nova-objects.json structure from client
    2. Creates/updates feature flags for each object
    3. Creates/updates default variants with default values
    4. Returns summary of operations performed
    """

    # Initialize CRUD instances
    flags_crud = FeatureFlagsCRUD(db)
    variants_crud = FeatureVariantsCRUD(db)

    # Track statistics
    stats = {
        "objects_processed": 0,
        "objects_created": 0,
        "objects_updated": 0,
        "objects_skipped": 0,
        "details": [],
    }

    # Process each object from the sync request
    for object_name, object_props in sync_request.objects.items():
        try:
            stats["objects_processed"] += 1

            # Check if feature flag already exists
            existing_flag = flags_crud.get_by_name(
                name=object_name,
                organisation_id=sync_request.organisation_id,
                app_id=sync_request.app_id,
            )

            keys_config = object_props.keys

            # TODO: Add keys_config validation here
            # Update existing flag
            if existing_flag:
                # Check if config has actually changed
                if existing_flag.keys_config != keys_config:
                    # Update the feature flag
                    updated_flag = flags_crud.update(
                        db_obj=existing_flag,
                        obj_in={
                            "keys_config": keys_config,
                            "type": object_props.type,
                        },
                    )

                    # Update or create default variant
                    default_variant_name = "default"
                    default_variant = variants_crud.get_by_name(
                        name=default_variant_name, feature_pid=existing_flag.pid
                    )
                    if default_variant:
                        # Update existing default variant
                        variants_crud.update(
                            db_obj=default_variant,
                            obj_in={
                                "config": updated_flag.default_variant,
                            },
                        )
                    else:
                        # Create new default variant
                        variants_crud.create(
                            obj_in={
                                "feature_id": existing_flag.pid,
                                "name": default_variant_name,
                                "config": updated_flag.default_variant,
                            }
                        )

                    stats["objects_updated"] += 1
                    stats["details"].append(
                        {
                            "object_name": object_name,
                            "action": "updated",
                            "flag_id": str(existing_flag.pid),
                            "message": "Updated feature flag and default variant",
                        }
                    )
                else:
                    # No changes needed
                    stats["objects_skipped"] += 1
                    stats["details"].append(
                        {
                            "object_name": object_name,
                            "action": "skipped",
                            "message": "No changes detected",
                        }
                    )

            else:
                # Create new feature flag with default variant
                flag_data = {
                    "name": object_name,
                    "description": f"Auto-generated from nova-objects.json for {object_name}",
                    "keys_config": keys_config,
                    "type": object_props.type,
                    "organisation_id": sync_request.organisation_id,
                    "app_id": sync_request.app_id,
                    "is_active": True,
                }

                new_flag = flags_crud.create(obj_in=flag_data)

                # Create default feature variant for the flag
                variants_crud.create(
                    obj_in={
                        "feature_id": new_flag.pid,
                        "name": "default",
                        "config": new_flag.default_variant,
                    }
                )

                stats["objects_created"] += 1
                stats["details"].append(
                    {
                        "object_name": object_name,
                        "action": "created",
                        "flag_id": str(new_flag.pid),
                        "message": "Created feature flag with default variant",
                    }
                )

        except Exception as obj_error:
            # Log error but continue with other objects
            stats["objects_skipped"] += 1
            stats["details"].append(
                {
                    "object_name": object_name,
                    "action": "error",
                    "message": f"Failed to process: {str(obj_error)}",
                }
            )
            traceback.print_exc()
            continue

    dashboard_url = f"https://dashboard.nova.com/apps/{sync_request.app_id}/objects"

    return NovaObjectSyncResponse(
        success=True,
        objects_processed=stats["objects_processed"],
        objects_created=stats["objects_created"],
        objects_updated=stats["objects_updated"],
        objects_skipped=stats["objects_skipped"],
        dashboard_url=dashboard_url,
        message=f"Processed {stats['objects_processed']} objects successfully",
        details=stats["details"],
    )


# @router.post("/", response_model=FeatureFlagResponse)
# async def create_feature_flag(
#     flag_data: FeatureFlagCreate, db: Session = Depends(get_db)
# ):
#     """Create a new feature flag with default variant"""
#     try:
#         feature_flags_crud = FeatureFlagsCRUD(db)

#         # Check if name already exists
#         existing = feature_flags_crud.get_by_name(
#             name=flag_data.name,
#             organisation_id=flag_data.organisation_id,
#             app_id=flag_data.app_id,
#         )
#         if existing:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Feature flag '{flag_data.name}' already exists",
#             )

#         # Create feature flag with default variant
#         feature_flag = feature_flags_crud.create(obj_in=flag_data.model_dump())

#         # Load with variants for response
#         feature_flag = feature_flags_crud.get_with_variants(pid=feature_flag.pid)
#         return feature_flag

#     except IntegrityError:
#         raise HTTPException(
#             status_code=400, detail="Feature flag with this name already exists"
#         )


@router.get(
    "/",
    response_model=List[FeatureFlagListItem],
    dependencies=[Depends(RoleRequired([
        AppRole.VIEWER, AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def list_feature_flags(
    organisation_id: str = Query(...),
    app_id: str = Query(...),
    active_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List feature flags with pagination"""
    feature_flags_crud = FeatureFlagsCRUD(db)

    if active_only:
        flags = feature_flags_crud.get_active_flags(
            organisation_id=organisation_id, app_id=app_id
        )
    else:
        flags = feature_flags_crud.get_multi(
            skip=skip, limit=limit, organisation_id=organisation_id, app_id=app_id
        )

    # Add variant count to each flag
    result = []
    for flag in flags:
        result.append(
            {
                "pid": flag.pid,
                "name": flag.name,
                "description": flag.description,
                "is_active": flag.is_active,
                "created_at": flag.created_at.isoformat(),
                "keys_config": flag.keys_config,
                "default_variant": flag.default_variant,
                "variants": flag.variants,
                "experience": flag.experience,
            }
        )

    return flags


@router.get("/available/", response_model=List[FeatureFlagListItem],
    dependencies=[Depends(RoleRequired([
        AppRole.VIEWER, AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def list_available_feature_flags(
    organisation_id: str = Query(...),
    app_id: str = Query(...),
    db: Session = Depends(get_db),
):
    """List feature flags that are not assigned to any experience"""
    feature_flags_crud = FeatureFlagsCRUD(db)

    flags = feature_flags_crud.get_available_flags(
        organisation_id=organisation_id, app_id=app_id
    )

    return flags


@router.get("/{flag_pid}/", response_model=FeatureFlagResponse,
    dependencies=[Depends(RoleRequired([
        AppRole.VIEWER, AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def get_feature_flag(flag_pid: UUID, db: Session = Depends(get_db)):
    """Get feature flag by ID with all variants"""
    feature_flags_crud = FeatureFlagsCRUD(db)

    feature_flag = feature_flags_crud.get_with_variants(pid=flag_pid)
    if not feature_flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    return feature_flag


@router.get("/{flag_pid}/details/", response_model=FeatureFlagDetailedResponse,
    dependencies=[Depends(RoleRequired([
        AppRole.VIEWER, AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def get_feature_flag_details(flag_pid: UUID, db: Session = Depends(get_db)):
    """Get feature flag with detailed information including usage statistics and experiences"""
    feature_flags_crud = FeatureFlagsCRUD(db)

    feature_flag = feature_flags_crud.get_with_full_details(pid=flag_pid)
    if not feature_flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    return feature_flag


@router.post("/{flag_pid}/variants/", response_model=VariantResponse,
    dependencies=[Depends(RoleRequired([
        AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def create_variant(
    flag_pid: UUID, variant_data: VariantCreate, db: Session = Depends(get_db)
):
    """Create a new variant for a feature flag"""
    feature_flags_crud = FeatureFlagsCRUD(db)
    feature_variants_crud = FeatureVariantsCRUD(db)

    # Check if feature flag exists
    feature_flag = feature_flags_crud.get_by_pid(flag_pid)
    if not feature_flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    # TODO: Add validation for variant_data based on keys_config

    # Check if variant name already exists
    existing_variant = feature_variants_crud.get_by_name(
        name=variant_data.name, feature_pid=flag_pid
    )
    if existing_variant:
        raise HTTPException(
            status_code=400, detail=f"Variant '{variant_data.name}' already exists"
        )

    # Create variant
    variant = feature_variants_crud.create_variant(
        feature_pid=flag_pid, variant_data=variant_data.model_dump()
    )
    return variant


@router.get("/{flag_pid}/variants/", response_model=List[VariantResponse],
    dependencies=[Depends(RoleRequired([
        AppRole.VIEWER, AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def get_feature_variants(flag_pid: UUID, db: Session = Depends(get_db)):
    """Get all variants for a feature flag"""
    feature_flags_crud = FeatureFlagsCRUD(db)
    feature_variants_crud = FeatureVariantsCRUD(db)

    # Check if feature flag exists
    feature_flag = feature_flags_crud.get_by_pid(flag_pid)
    if not feature_flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    variants = feature_variants_crud.get_feature_variants(feature_pid=flag_pid)
    return variants


@router.put("/variants/{variant_pid}/", response_model=VariantResponse,
    dependencies=[Depends(RoleRequired([
        AppRole.ANALYST, AppRole.DEVELOPER, AppRole.ADMIN, AppRole.OWNER
    ]))]
)
async def update_variant(
    variant_pid: UUID, variant_data: VariantCreate, db: Session = Depends(get_db)
):
    """Update a variant"""
    feature_variants_crud = FeatureVariantsCRUD(db)

    variant = feature_variants_crud.get_by_pid(variant_pid)
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    # TODO: Add validation for variant_data based on keys_config

    # Check if new name conflicts with existing variants in the same feature
    if variant_data.name != variant.name:
        existing = feature_variants_crud.get_by_name(
            name=variant_data.name, feature_pid=variant.feature_id
        )
        if existing:
            raise HTTPException(
                status_code=400, detail=f"Variant '{variant_data.name}' already exists"
            )

    # Update variant
    updated_variant = feature_variants_crud.update(
        db_obj=variant, obj_in=variant_data.model_dump()
    )
    return updated_variant
