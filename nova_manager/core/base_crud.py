from typing import Optional, List, Dict, Any
from uuid import UUID as UUIDType
from sqlalchemy.orm import Session


class BaseCRUD:
    """Base CRUD class with common operations"""

    def __init__(self, model, db: Session):
        self.model = model
        self.db = db

    def get_by_id(self, id: int) -> Optional[Any]:
        """Get record by integer ID"""
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_by_pid(self, pid: UUIDType) -> Optional[Any]:
        """Get record by UUID PID"""
        return self.db.query(self.model).filter(self.model.pid == pid).first()

    def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        organisation_id: Optional[str] = None,
        app_id: Optional[str] = None,
    ) -> List[Any]:
        """Get multiple records with pagination and filtering"""
        query = self.db.query(self.model)

        # Add organisation/app filtering if model has these fields
        if hasattr(self.model, "organisation_id") and organisation_id:
            query = query.filter(self.model.organisation_id == organisation_id)
        if hasattr(self.model, "app_id") and app_id:
            query = query.filter(self.model.app_id == app_id)

        return query.offset(skip).limit(limit).all()

    def create(self, obj_in: Dict[str, Any]) -> Any:
        """Create new record"""
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: Any, obj_in: Dict[str, Any]) -> Any:
        """Update existing record"""
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: int) -> Any:
        """Delete record by integer ID"""
        obj = self.db.query(self.model).get(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj

    def delete_by_pid(self, pid: UUIDType) -> Any:
        """Delete record by UUID PID"""
        obj = self.get_by_pid(pid)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj
