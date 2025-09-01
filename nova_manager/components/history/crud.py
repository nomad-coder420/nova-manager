from nova_manager.core.base_crud import BaseCRUD
from nova_manager.components.history.models import HistoryLog


class HistoryCRUD(BaseCRUD):
    """
    CRUD for HistoryLog. Use create_entry to archive objects before changes.
    """
    def __init__(self, db):
        super().__init__(HistoryLog, db)

    def create_entry(self, *, action: str, object_type: str, object_id, data: dict):
        """
        Insert a history record.
        action: e.g. 'EDIT' or 'DELETE'
        object_type: table name or logical name
        object_id: UUID of the object being changed
        data: full object serialized to JSON
        """
        payload = {
            "action": action,
            "object_type": object_type,
            "object_id": object_id,
            "data": data,
        }
        return self.create(payload)
