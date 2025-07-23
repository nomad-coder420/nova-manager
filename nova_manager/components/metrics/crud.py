from uuid import UUID
from nova_manager.components.metrics.models import EventsSchema, Metrics
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
