from uuid import UUID
from nova_manager.components.metrics.models import (
    EventsSchema,
    Metrics,
    PersonalisationMetrics,
    UserProfileKeys,
)
from nova_manager.core.base_crud import BaseCRUD
from sqlalchemy import and_, asc, desc
from sqlalchemy.orm import Session


class MetricsCRUD(BaseCRUD):
    def __init__(self, db: Session):
        super().__init__(Metrics, db)

    def get_metric(self, metric_id: UUID) -> Metrics | None:
        return self.db.query(Metrics).filter(self.model.pid == metric_id).first()


class EventsSchemaCRUD(BaseCRUD):
    def __init__(self, db: Session):
        super().__init__(EventsSchema, db)

    def get_event_schema(
        self, event_name: str, organisation_id: str, app_id: str
    ) -> EventsSchema | None:
        return (
            self.db.query(EventsSchema)
            .filter(
                EventsSchema.event_name == event_name,
                EventsSchema.organisation_id == organisation_id,
                EventsSchema.app_id == app_id,
            )
            .first()
        )

    def get_events_schema(
        self, event_names: list[str], organisation_id: str, app_id: str
    ) -> list[EventsSchema]:
        return (
            self.db.query(EventsSchema)
            .filter(
                EventsSchema.event_name.in_(event_names),
                EventsSchema.organisation_id == organisation_id,
                EventsSchema.app_id == app_id,
            )
            .all()
        )

    def get_multi_by_org(
        self,
        organisation_id: str,
        app_id: str,
        skip: int = 0,
        limit: int = 10,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> list[EventsSchema]:
        """Get experiences for organization/app with pagination and filtering"""
        query = self.db.query(EventsSchema).filter(
            and_(
                EventsSchema.organisation_id == organisation_id,
                EventsSchema.app_id == app_id,
            )
        )

        # Apply ordering
        order_column = getattr(EventsSchema, order_by, EventsSchema.created_at)

        if order_direction.lower() == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))

        return query.offset(skip).limit(limit).all()

    def search_events_schema(
        self,
        organisation_id: str,
        app_id: str,
        search_term: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EventsSchema]:
        """Search events schema by name"""
        search_pattern = f"%{search_term}%"

        return (
            self.db.query(EventsSchema)
            .filter(
                and_(
                    EventsSchema.organisation_id == organisation_id,
                    EventsSchema.app_id == app_id,
                    EventsSchema.event_name.ilike(search_pattern),
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def bulk_create(self, event_schemas: list[EventsSchema]):
        self.db.bulk_save_objects(event_schemas)
        self.db.commit()

    def bulk_update(self, event_schemas: list[EventsSchema]):
        for obj in event_schemas:
            self.db.add(obj)

        self.db.commit()


class PersonalisationMetricsCRUD(BaseCRUD):
    def __init__(self, db: Session):
        super().__init__(PersonalisationMetrics, db)

    def get_by_personalisation(
        self, personalisation_id: UUID
    ) -> list[PersonalisationMetrics]:
        """Get all metrics for a personalisation"""
        return (
            self.db.query(PersonalisationMetrics)
            .filter(PersonalisationMetrics.personalisation_id == personalisation_id)
            .all()
        )

    def get_by_metric(self, metric_id: UUID) -> list[PersonalisationMetrics]:
        """Get all personalisations using a specific metric"""
        return (
            self.db.query(PersonalisationMetrics)
            .filter(PersonalisationMetrics.metric_id == metric_id)
            .all()
        )

    def create_personalisation_metric(
        self, personalisation_id: UUID, metric_id: UUID
    ) -> PersonalisationMetrics:
        """Create association between personalisation and metric"""
        personalisation_metric = PersonalisationMetrics(
            personalisation_id=personalisation_id, metric_id=metric_id
        )
        self.db.add(personalisation_metric)
        self.db.flush()
        self.db.refresh(personalisation_metric)
        return personalisation_metric

    def delete_personalisation_metrics(
        self, personalisation_id: UUID, metric_ids: list[str]
    ) -> int:
        """Delete specific metric associations for a personalisation"""
        if not metric_ids:
            return 0

        deleted_count = (
            self.db.query(PersonalisationMetrics)
            .filter(
                PersonalisationMetrics.personalisation_id == personalisation_id,
                PersonalisationMetrics.metric_id.in_(metric_ids),
            )
            .delete()
        )

        return deleted_count

    def exists(self, personalisation_id: UUID, metric_id: UUID) -> bool:
        """Check if association already exists"""
        return (
            self.db.query(PersonalisationMetrics)
            .filter(
                PersonalisationMetrics.personalisation_id == personalisation_id,
                PersonalisationMetrics.metric_id == metric_id,
            )
            .first()
        ) is not None


class UserProfileKeysCRUD(BaseCRUD):
    def __init__(self, db: Session):
        super().__init__(UserProfileKeys, db)

    def get_user_profile_key(
        self, key: str, organisation_id: str, app_id: str
    ) -> UserProfileKeys | None:
        """Get a specific user profile key for org/app"""
        return (
            self.db.query(UserProfileKeys)
            .filter(
                UserProfileKeys.key == key,
                UserProfileKeys.organisation_id == organisation_id,
                UserProfileKeys.app_id == app_id,
            )
            .first()
        )

    def get_user_profile_keys(
        self, keys: list[str], organisation_id: str, app_id: str
    ) -> list[UserProfileKeys]:
        """Get multiple user profile keys by key names for org/app in a single query"""
        return (
            self.db.query(UserProfileKeys)
            .filter(
                UserProfileKeys.key.in_(keys),
                UserProfileKeys.organisation_id == organisation_id,
                UserProfileKeys.app_id == app_id,
            )
            .all()
        )

    def get_multi_by_org(
        self,
        organisation_id: str,
        app_id: str,
        skip: int = 0,
        limit: int = 10,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> list[UserProfileKeys]:
        """Get user profile keys for organization/app with pagination and filtering"""
        query = self.db.query(UserProfileKeys).filter(
            and_(
                UserProfileKeys.organisation_id == organisation_id,
                UserProfileKeys.app_id == app_id,
            )
        )

        # Apply ordering
        order_column = getattr(UserProfileKeys, order_by, UserProfileKeys.created_at)

        if order_direction.lower() == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))

        return query.offset(skip).limit(limit).all()

    def search_user_profile_keys(
        self,
        organisation_id: str,
        app_id: str,
        search_term: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[UserProfileKeys]:
        """Search user profile keys by key name or description"""
        return (
            self.db.query(UserProfileKeys)
            .filter(
                UserProfileKeys.organisation_id == organisation_id,
                UserProfileKeys.app_id == app_id,
                (
                    UserProfileKeys.key.ilike(f"%{search_term}%")
                    | UserProfileKeys.description.ilike(f"%{search_term}%")
                ),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_user_profile_key(
        self,
        key: str,
        key_type: str,
        organisation_id: str,
        app_id: str,
        description: str = "",
    ) -> UserProfileKeys:
        """Create a new user profile key"""
        user_profile_key = UserProfileKeys(
            key=key,
            type=key_type,
            description=description,
            organisation_id=organisation_id,
            app_id=app_id,
        )
        self.db.add(user_profile_key)
        self.db.flush()
        self.db.refresh(user_profile_key)
        return user_profile_key

    def create_user_profile_keys_if_not_exists(
        self, user_profile_data: dict, organisation_id: str, app_id: str
    ) -> list[UserProfileKeys]:
        """Create user profile keys for new keys that don't exist yet"""
        # Get all keys from user_profile_data
        keys_to_check = list(user_profile_data.keys())

        # Fetch all existing keys in a single query
        existing_keys = self.get_user_profile_keys(
            keys_to_check, organisation_id, app_id
        )

        # Create a set of existing key names for fast lookup
        existing_key_names = {key.key for key in existing_keys}

        # Collect new keys to create in bulk
        keys_to_create = []
        for key, value in user_profile_data.items():
            # Check if key already exists using the pre-fetched data
            if key not in existing_key_names:
                # Determine type based on value
                key_type = self._infer_type_from_value(value)

                keys_to_create.append(
                    UserProfileKeys(
                        key=key,
                        type=key_type,
                        description=f"Auto-generated key for {key}",
                        organisation_id=organisation_id,
                        app_id=app_id,
                    )
                )

        # Bulk create all new keys in a single operation
        if keys_to_create:
            return self.bulk_create_user_profile_keys(keys_to_create)

        return []

    def bulk_create_user_profile_keys(
        self, user_profile_keys: list[UserProfileKeys]
    ) -> list[UserProfileKeys]:
        """Bulk create multiple user profile keys"""

        self.db.bulk_save_objects(user_profile_keys, return_defaults=True)
        self.db.commit()

        return user_profile_keys

    def exists(self, key: str, organisation_id: str, app_id: str) -> bool:
        """Check if user profile key exists"""
        return self.get_user_profile_key(key, organisation_id, app_id) is not None

    def update_user_profile_key(
        self,
        key: str,
        organisation_id: str,
        app_id: str,
        key_type: str | None = None,
        description: str | None = None,
    ) -> UserProfileKeys | None:
        """Update an existing user profile key"""
        existing_key = self.get_user_profile_key(key, organisation_id, app_id)

        if existing_key:
            if key_type is not None:
                existing_key.type = key_type
            if description is not None:
                existing_key.description = description

            self.db.flush()
            self.db.refresh(existing_key)
            return existing_key

        return None

    def delete_user_profile_key(
        self, key: str, organisation_id: str, app_id: str
    ) -> bool:
        """Delete a user profile key"""
        existing_key = self.get_user_profile_key(key, organisation_id, app_id)

        if existing_key:
            self.db.delete(existing_key)
            self.db.flush()
            return True

        return False

    def _infer_type_from_value(self, value) -> str:
        """Infer the type of a user profile key from its value"""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            return "string"
        else:
            return "string"  # Default to string for unknown types
