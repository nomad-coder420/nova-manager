import re


class EventsArtefacts:
    def __init__(self, organisation_id: str, app_id: str):
        self.organisation_id = organisation_id
        self.app_id = app_id
        self.dataset_name = self._dataset_name(organisation_id, app_id)

    def _dataset_name(self) -> str:
        return f"org_{self.organisation_id}_app_{self.app_id}"

    def _sanitized_string(self, s: str):
        return re.sub(r"[^a-zA-Z0-9_]", "_", s)

    def _event_table_name(self, event_name: str) -> str:
        safe_event_name = self._sanitized_string(event_name)
        return f"`{self.dataset_name}.events_{safe_event_name}`"

    def _event_props_table_name(self, event_name: str) -> str:
        safe_event_name = self._sanitized_string(event_name)
        return f"`{self.dataset_name}.event_{safe_event_name}_props`"
