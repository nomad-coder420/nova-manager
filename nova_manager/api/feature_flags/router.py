from typing import Dict, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError


from nova_manager.api.feature_flags.request_response import (
    FeatureFlagCreate,
    FeatureFlagListItem,
    FeatureFlagResponse,
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
    IndividualTargetingCRUD,
    TargetingRulesCRUD,
)
from nova_manager.database.session import get_db


router = APIRouter()


@router.post("/sync-nova-objects/")
async def sync_nova_objects(
    sync_request: NovaObjectSyncRequest, db: Session = Depends(get_db)
):
    """
    Sync Nova objects from client application to create/update feature flags

    This endpoint:
    1. Takes nova-objects.json structure from client
    2. Creates/updates feature flags for each object
    3. Creates default variants with the provided properties
    4. Returns summary of operations performed
    """

    # Initialize CRUD instances
    flags_crud = FeatureFlagsCRUD(db)

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

            if existing_flag:
                # Update existing flag
                # Check if config has actually changed
                if existing_flag.keys_config != keys_config:
                    updated_variant = flags_crud.update(
                        db_obj=existing_flag, obj_in={"keys_config": keys_config}
                    )

                    stats["objects_updated"] += 1
                    stats["details"].append(
                        {
                            "object_name": object_name,
                            "action": "updated",
                            "flag_id": str(existing_flag.pid),
                            "message": "Updated default variant properties",
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
                    "organisation_id": sync_request.organisation_id,
                    "app_id": sync_request.app_id,
                    "is_active": True,
                }

                new_flag = flags_crud.create(obj_in=flag_data)

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


@router.post("/", response_model=FeatureFlagResponse)
async def create_feature_flag(
    flag_data: FeatureFlagCreate, db: Session = Depends(get_db)
):
    """Create a new feature flag with default variant"""
    try:
        feature_flags_crud = FeatureFlagsCRUD(db)

        # Check if name already exists
        existing = feature_flags_crud.get_by_name(
            name=flag_data.name,
            organisation_id=flag_data.organisation_id,
            app_id=flag_data.app_id,
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Feature flag '{flag_data.name}' already exists",
            )

        # Create feature flag with default variant
        feature_flag = feature_flags_crud.create(obj_in=flag_data.model_dump())

        # Load with variants for response
        feature_flag = feature_flags_crud.get_with_variants(pid=feature_flag.pid)
        return feature_flag

    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Feature flag with this name already exists"
        )


@router.get("/", response_model=List[FeatureFlagListItem])
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
            }
        )

    return result


@router.get("/{flag_pid}/", response_model=FeatureFlagResponse)
async def get_feature_flag(flag_pid: UUID, db: Session = Depends(get_db)):
    """Get feature flag by ID with all variants"""
    feature_flags_crud = FeatureFlagsCRUD(db)

    feature_flag = feature_flags_crud.get_with_variants(pid=flag_pid)
    if not feature_flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    return feature_flag


@router.put("/{flag_pid}/", response_model=FeatureFlagResponse)
async def update_feature_flag(
    flag_pid: UUID, flag_update: FeatureFlagUpdate, db: Session = Depends(get_db)
):
    """Update feature flag"""
    feature_flags_crud = FeatureFlagsCRUD(db)

    feature_flag = feature_flags_crud.get_by_pid(flag_pid)
    if not feature_flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    # Update only provided fields
    update_data = flag_update.model_dump(exclude_unset=True)
    if update_data:
        try:
            feature_flag = feature_flags_crud.update(
                db_obj=feature_flag, obj_in=update_data
            )
        except IntegrityError:
            raise HTTPException(
                status_code=400, detail="Feature flag with this name already exists"
            )

    # Return with variants
    return feature_flags_crud.get_with_variants(pid=flag_pid)


@router.delete("/{flag_pid}/")
async def delete_feature_flag(flag_pid: UUID, db: Session = Depends(get_db)):
    """Delete feature flag"""
    feature_flags_crud = FeatureFlagsCRUD(db)

    feature_flag = feature_flags_crud.get_by_pid(flag_pid)
    if not feature_flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    feature_flags_crud.delete_by_pid(pid=flag_pid)
    return {"message": "Feature flag deleted successfully"}


@router.post("/{flag_pid}/toggle/")
async def toggle_feature_flag(flag_pid: UUID, db: Session = Depends(get_db)):
    """Toggle feature flag active status"""
    feature_flags_crud = FeatureFlagsCRUD(db)

    feature_flag = feature_flags_crud.toggle_active(pid=flag_pid)
    if not feature_flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    return {
        "message": f"Feature flag {'activated' if feature_flag.is_active else 'deactivated'}",
        "is_active": feature_flag.is_active,
    }


@router.post("/{flag_pid}/variants/", response_model=VariantResponse)
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


@router.get("/{flag_pid}/variants/", response_model=List[VariantResponse])
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


@router.put("/variants/{variant_pid}/", response_model=VariantResponse)
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


@router.delete("/variants/{variant_pid}/")
async def delete_variant(variant_pid: UUID, db: Session = Depends(get_db)):
    """Delete a variant"""
    feature_variants_crud = FeatureVariantsCRUD(db)

    variant = feature_variants_crud.get_by_pid(variant_pid)
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    feature_variants_crud.delete_by_pid(pid=variant_pid)
    return {"message": "Variant deleted successfully"}


@router.get("/{flag_pid}/targeting-rules/")
async def get_targeting_rules(flag_pid: UUID, db: Session = Depends(get_db)):
    """Get all targeting rules for a feature flag"""
    feature_flags_crud = FeatureFlagsCRUD(db)
    targeting_rules_crud = TargetingRulesCRUD(db)

    feature_flag = feature_flags_crud.get_by_pid(flag_pid)
    if not feature_flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    rules = targeting_rules_crud.get_feature_rules(feature_pid=flag_pid)
    return [
        {
            "pid": rule.pid,
            "priority": rule.priority,
            "rule_config": rule.rule_config,
            "created_at": rule.created_at.isoformat(),
            "modified_at": rule.modified_at.isoformat(),
        }
        for rule in rules
    ]


@router.post("/{flag_pid}/targeting-rules/")
async def create_targeting_rule(
    flag_pid: UUID, rule_data: TargetingRuleCreate, db: Session = Depends(get_db)
):
    """Create a new targeting rule"""
    feature_flags_crud = FeatureFlagsCRUD(db)
    targeting_rules_crud = TargetingRulesCRUD(db)

    feature_flag = feature_flags_crud.get_by_pid(flag_pid)
    if not feature_flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    try:
        rule = targeting_rules_crud.create_rule(
            feature_pid=flag_pid,
            rule_config=rule_data.rule_config,
            priority=rule_data.priority,
        )
        return {
            "pid": rule.pid,
            "priority": rule.priority,
            "rule_config": rule.rule_config,
            "created_at": rule.created_at.isoformat(),
            "message": "Targeting rule created successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/targeting-rules/{rule_pid}/")
async def update_targeting_rule(
    rule_pid: UUID, rule_data: TargetingRuleCreate, db: Session = Depends(get_db)
):
    """Update a targeting rule"""
    targeting_rules_crud = TargetingRulesCRUD(db)

    rule = targeting_rules_crud.get_by_pid(rule_pid)
    if not rule:
        raise HTTPException(status_code=404, detail="Targeting rule not found")

    # Update priority if changed
    if rule_data.priority != rule.priority:
        targeting_rules_crud.update_priority(
            pid=rule_pid, new_priority=rule_data.priority
        )

    # Update config
    updated_rule = targeting_rules_crud.update_config(
        pid=rule_pid, rule_config=rule_data.rule_config
    )

    return {
        "pid": updated_rule.pid,
        "priority": updated_rule.priority,
        "rule_config": updated_rule.rule_config,
        "modified_at": updated_rule.modified_at.isoformat(),
        "message": "Targeting rule updated successfully",
    }


@router.delete("/targeting-rules/{rule_pid}/")
async def delete_targeting_rule(rule_pid: UUID, db: Session = Depends(get_db)):
    """Delete a targeting rule"""
    targeting_rules_crud = TargetingRulesCRUD(db)

    rule = targeting_rules_crud.get_by_pid(rule_pid)
    if not rule:
        raise HTTPException(status_code=404, detail="Targeting rule not found")

    targeting_rules_crud.delete_by_pid(pid=rule_pid)
    return {"message": "Targeting rule deleted successfully"}


@router.get("/{flag_pid}/individual-targeting/")
async def get_individual_targeting(flag_pid: UUID, db: Session = Depends(get_db)):
    """Get all individual targeting rules for a feature flag"""
    feature_flags_crud = FeatureFlagsCRUD(db)
    individual_targeting_crud = IndividualTargetingCRUD(db)

    feature_flag = feature_flags_crud.get_by_pid(flag_pid)
    if not feature_flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    rules = individual_targeting_crud.get_feature_individual_targeting(
        feature_pid=flag_pid
    )
    return [
        {
            "pid": rule.pid,
            "rule_config": rule.rule_config,
            "created_at": rule.created_at.isoformat(),
            "modified_at": rule.modified_at.isoformat(),
        }
        for rule in rules
    ]


@router.post("/{flag_pid}/individual-targeting/")
async def create_individual_targeting(
    flag_pid: UUID,
    targeting_data: IndividualTargetingCreate,
    db: Session = Depends(get_db),
):
    """Create a new individual targeting rule"""
    feature_flags_crud = FeatureFlagsCRUD(db)
    individual_targeting_crud = IndividualTargetingCRUD(db)

    feature_flag = feature_flags_crud.get_by_pid(flag_pid)
    if not feature_flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    targeting = individual_targeting_crud.create_individual_targeting(
        feature_pid=flag_pid, rule_config=targeting_data.rule_config
    )

    return {
        "pid": targeting.pid,
        "rule_config": targeting.rule_config,
        "created_at": targeting.created_at.isoformat(),
        "message": "Individual targeting rule created successfully",
    }


@router.put("/individual-targeting/{targeting_pid}/")
async def update_individual_targeting(
    targeting_pid: UUID,
    targeting_data: IndividualTargetingCreate,
    db: Session = Depends(get_db),
):
    """Update an individual targeting rule"""
    individual_targeting_crud = IndividualTargetingCRUD(db)

    targeting = individual_targeting_crud.get_by_pid(targeting_pid)
    if not targeting:
        raise HTTPException(
            status_code=404, detail="Individual targeting rule not found"
        )

    updated_targeting = individual_targeting_crud.update_config(
        pid=targeting_pid, rule_config=targeting_data.rule_config
    )

    return {
        "pid": updated_targeting.pid,
        "rule_config": updated_targeting.rule_config,
        "modified_at": updated_targeting.modified_at.isoformat(),
        "message": "Individual targeting rule updated successfully",
    }


@router.delete("/individual-targeting/{targeting_pid}/")
async def delete_individual_targeting(
    targeting_pid: UUID, db: Session = Depends(get_db)
):
    """Delete an individual targeting rule"""
    individual_targeting_crud = IndividualTargetingCRUD(db)

    targeting = individual_targeting_crud.get_by_pid(targeting_pid)
    if not targeting:
        raise HTTPException(
            status_code=404, detail="Individual targeting rule not found"
        )

    individual_targeting_crud.delete_by_pid(pid=targeting_pid)
    return {"message": "Individual targeting rule deleted successfully"}
