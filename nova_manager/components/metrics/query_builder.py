from datetime import date
import re
from typing import Literal, TypedDict


class TimeRange(TypedDict):
    start: str
    end: str


class EventFilter(TypedDict):
    event_name: str
    filters: dict | None


class BaseMetricConfig(TypedDict):
    group_by: list[str]
    filters: dict


class CountMetricConfig(BaseMetricConfig):
    event_name: str
    distinct: bool


class AggregationMetricConfig(BaseMetricConfig):
    event_name: str
    property: str
    aggregation: Literal["sum", "avg", "min", "max"]


class RatioMetricConfig(BaseMetricConfig):
    numerator: EventFilter
    denominator: EventFilter


class RetentionMetricConfig(BaseMetricConfig):
    initial_event: EventFilter
    return_event: EventFilter
    retention_window: str


GRANULARITY_TRUNC_MAP = {
    "hourly": "TIMESTAMP_TRUNC({ts}, HOUR)",
    "daily": "DATE_TRUNC({ts}, DAY)",
    "weekly": "DATE_TRUNC({ts}, WEEK)",
    "monthly": "DATE_TRUNC({ts}, MONTH)",
    "none": "TIMESTAMP('1970-01-01 00:00:00')",
}

UNIT_SQL_MAP = {
    "h": "HOUR",
    "d": "DAY",
    "w": "WEEK",
}

CORE_FIELDS = {"event_name", "user_id", "org_id", "app_id"}


class QueryBuilder:
    def __init__(self, organisation_id: str, app_id: str):
        self.organisation_id = organisation_id
        self.app_id = app_id
        self.dataset_name = self._dataset_name()

    def build_query(
        self,
        metric_type: Literal["count", "aggregation", "ratio", "retention"],
        metric_config: (
            CountMetricConfig
            | AggregationMetricConfig
            | RatioMetricConfig
            | RetentionMetricConfig
        ),
    ) -> str:
        if metric_type == "count":
            return self._build_count_query(metric_config)

        elif metric_type == "aggregation":
            return self._build_aggregation_query(metric_config)

        elif metric_type == "ratio":
            return self._build_ratio_query(metric_config)

        elif metric_type == "retention":
            return self._build_retention_query(metric_config)

        raise Exception(f"Unsupported metric_type: {metric_type}")

    def _build_count_query(self, metric_config: CountMetricConfig):
        granularity = metric_config.get("granularity")
        time_range = metric_config.get("time_range")
        group_by = metric_config.get("group_by") or []
        filters = metric_config.get("filters") or {}

        event_name = metric_config.get("event_name") or ""
        distinct = metric_config.get("distinct") or False

        start = time_range.get("start") or ""
        end = time_range.get("end") or ""

        select_parts = self._get_select_parts(metric_config)

        count_expression = "COUNT(DISTINCT e.user_id)" if distinct else "COUNT(*)"
        select_parts.append(count_expression)

        select_expression = "SELECT " + ",\n    ".join(select_parts)

        table_name = self._event_table_name(event_name)
        from_expression = f"FROM {table_name} AS e"

        wheres, where_joins = self._wheres_and_joins(event_name, filters)

        where_expression = (
            f"WHERE e.server_ts >= '{start}' AND e.server_ts < '{end}'"
            + (" AND " + " AND ".join(wheres) if wheres else "")
        )

        group_props_join_expression = self._group_props_join_expression(
            event_name, group_by
        )

        join_expression = "\n".join(where_joins + group_props_join_expression)

        group_by_expression = "GROUP BY " + ", ".join(["period"] + group_by)

        order_expression = "ORDER BY period"

        return self._format_query(
            select_expression,
            from_expression,
            join_expression=join_expression,
            where_expression=where_expression,
            group_by_expression=group_by_expression,
            order_expression=order_expression,
        )

    def _build_aggregation_query(self, metric_config: AggregationMetricConfig):
        granularity = metric_config.get("granularity")
        time_range = metric_config.get("time_range")
        group_by = metric_config.get("group_by") or []
        filters = metric_config.get("filters") or {}

        event_name = metric_config.get("event_name") or ""
        aggregation = metric_config.get("aggregation")
        property = metric_config.get("property")

        start = time_range.get("start") or ""
        end = time_range.get("end") or ""

        select_parts = self._get_select_parts(metric_config)

        metric_alias = f"{aggregation.lower()}_{property}"
        aggregation_expression = (
            f"{aggregation.upper()}(CAST(p_val.value AS FLOAT64)) AS {metric_alias}"
        )
        select_parts.append(aggregation_expression)

        select_expression = "SELECT " + ",\n    ".join(select_parts)

        table_name = self._event_table_name(event_name)
        from_expression = f"FROM {table_name} AS e"

        wheres, where_joins = self._wheres_and_joins(event_name, filters)

        where_expression = (
            f"WHERE e.server_ts >= '{start}' AND e.server_ts < '{end}'"
            + (" AND " + " AND ".join(wheres) if wheres else "")
        )

        group_props_join_expression = self._group_props_join_expression(
            event_name, group_by
        )

        join_expression = "\n".join(where_joins + group_props_join_expression)

        group_by_expression = "GROUP BY " + ", ".join(["period"] + group_by)

        return self._format_query(
            select_expression,
            from_expression,
            join_expression=join_expression,
            where_expression=where_expression,
            group_by_expression=group_by_expression,
        )

    def _build_ratio_query(self, metric_config: RatioMetricConfig):
        granularity = metric_config.get("granularity")
        time_range = metric_config.get("time_range")
        group_by = metric_config.get("group_by") or []
        filters = metric_config.get("filters") or {}

        numerator_config = metric_config.get("numerator")
        numerator_filters = numerator_config.get("filters") or {}
        numerator_filters.update(filters)

        numerator_expression = self._build_count_query(
            {
                "event_name": numerator_config.get("event_name"),
                "distinct": False,
                "time_range": time_range,
                "granularity": granularity,
                "group_by": group_by,
                "filters": numerator_filters,
            }
        )

        denominator_config = metric_config.get("denominator")
        denominator_filters = denominator_config.get("filters") or {}
        denominator_filters.update(filters)

        denominator_expression = self._build_count_query(
            {
                "event_name": denominator_config.get("event_name"),
                "distinct": False,
                "time_range": time_range,
                "granularity": granularity,
                "group_by": group_by,
                "filters": denominator_filters,
            }
        )

        with_expression = f"WITH\n num AS (\n{numerator_expression}\n),\n den AS (\n{denominator_expression}\n)"

        select_parts = [
            "num.period",
            f"SAFE_DIVIDE(num.num_val, den.den_val) AS ratio",
        ] + [f"num.{c}" for c in group_by]
        select_expression = "SELECT " + ",\n    ".join(select_parts)

        from_expression = "FROM num"

        group_by_join_conditions = [
            f"IFNULL(num.{c},'') = IFNULL(den.{c},'')" for c in group_by
        ]
        join_conditions = ["num.period = den.period"] + group_by_join_conditions
        join_expression = "JOIN den ON " + " AND ".join(join_conditions)

        order_by_expression = "ORDER BY num.period"

        return self._format_query(
            select_expression,
            from_expression,
            join_expression=join_expression,
            order_expression=order_by_expression,
            with_expression=with_expression,
        )

    # TODO: Review this query
    def _build_retention_query(self, metric_config: RetentionMetricConfig):
        granularity = metric_config.get("granularity")
        time_range = metric_config.get("time_range")
        group_by = metric_config.get("group_by") or []
        filters = metric_config.get("filters") or {}

        initial_event = metric_config.get("initial_event")
        return_event = metric_config.get("return_event")
        retention_window = metric_config.get("retention_window")

        start = time_range.get("start") or ""
        end = time_range.get("end") or ""

        window_sql = self._interval_sql(retention_window)
        bucket_expr = self._time_bucket("e.server_ts", granularity)

        # Initial cohort CTE
        initial_event_name = initial_event.get("event_name")
        initial_filters = initial_event.get("filters") or {}
        initial_filters.update(filters)

        g_selects = self._group_selects(group_by, "e")
        g_joins = self._group_props_join_expression(initial_event_name, group_by)
        f_where_init, f_joins_init = self._wheres_and_joins(
            initial_event_name, initial_filters
        )

        init_select_cols = (
            [f"{bucket_expr} AS cohort_period"]
            + g_selects
            + [
                "e.user_id AS user_id",
                "MIN(e.server_ts) AS first_ts",
            ]
        )

        init_group_clause = ", ".join(["cohort_period", "user_id"] + group_by)

        init_cte = (
            "initial_cohort AS (\n    SELECT\n        "
            + ",\n        ".join(init_select_cols)
            + f"\n    FROM {self._event_table_name(initial_event_name)} AS e\n    "
            + "\n    ".join(g_joins + f_joins_init)
            + f"\n    WHERE e.server_ts >= '{start}' AND e.server_ts < '{end}'{' AND ' + ' AND '.join(f_where_init) if f_where_init else ''}\n"
            + f"    GROUP BY {init_group_clause}\n)"
        )

        # Return events CTE
        return_event_name = return_event.get("event_name")
        return_filters = return_event.get("filters") or {}
        return_filters.update(filters)

        f_where_ret, f_joins_ret = self._wheres_and_joins(
            return_event_name, return_filters
        )
        ret_cte = (
            "return_events AS (\n    SELECT\n        r.user_id AS user_id,\n        r.server_ts AS ret_ts\n    FROM "
            + self._event_table_name(return_event_name)
            + " AS r\n    "
            + "\n    ".join(f_joins_ret)
            + f"\n    WHERE r.server_ts >= '{start}' AND r.server_ts < '{end}'{' AND ' + ' AND '.join(f_where_ret) if f_where_ret else ''}\n)"
        )

        # Final select
        select_cols = ["i.cohort_period"] + [f"i.{c}" for c in group_by]
        select_list = ", ".join(select_cols)
        group_clause = ", ".join(select_cols)

        final_sql = (
            "SELECT\n    "
            + select_list
            + ",\n    COUNT(DISTINCT i.user_id) AS cohort_users,\n    COUNT(DISTINCT IF(r.ret_ts IS NOT NULL, i.user_id, NULL)) AS retained_users,\n    SAFE_DIVIDE(COUNT(DISTINCT IF(r.ret_ts IS NOT NULL, i.user_id, NULL)), COUNT(DISTINCT i.user_id)) AS retention_rate"
            + f"\nFROM initial_cohort i\nLEFT JOIN return_events r\n  ON r.user_id = i.user_id\n  AND r.ret_ts > i.first_ts\n  AND r.ret_ts < TIMESTAMP_ADD(i.first_ts, {window_sql})\nGROUP BY {group_clause}\nORDER BY i.cohort_period"
        )

        return f"WITH\n{init_cte},\n{ret_cte}\n{final_sql}"

    def _format_query(
        self,
        select_expression: str,
        from_expression: str,
        join_expression: str | None = None,
        where_expression: str | None = None,
        group_by_expression: str | None = None,
        order_expression: str | None = None,
        with_expression: str | None = None,
    ) -> str:
        query = f"{select_expression}\n{from_expression}"

        if join_expression:
            query += f"\n{join_expression}"

        if where_expression:
            query += f"\n{where_expression}"

        if group_by_expression:
            query += f"\n{group_by_expression}"

        if order_expression:
            query += f"\n{order_expression}"

        if with_expression:
            query = f"{with_expression}\n" + query

        return query

    def _time_bucket(self, column_name: str, granularity: str) -> str:
        if granularity not in GRANULARITY_TRUNC_MAP:
            raise ValueError(f"Unsupported time granularity: {granularity}")

        return GRANULARITY_TRUNC_MAP[granularity].format(ts=column_name)

    def _dataset_name(self) -> str:
        return f"org_{self.organisation_id}_app_{self.app_id}"

    def _event_table_name(self, event_name: str) -> str:
        return f"`{self.dataset_name}.events_{event_name}`"

    def _event_props_table_name(self, event_name: str) -> str:
        return f"`{self.dataset_name}.event_{event_name}_props`"

    def _get_select_parts(self, metric_config: BaseMetricConfig):
        granularity = metric_config.get("granularity")
        group_by = metric_config.get("group_by") or []

        time_bucket = self._time_bucket("e.server_ts", granularity)
        group_selects = self._group_selects(group_by, "e")

        period_expression = f"{time_bucket} AS period"

        return [period_expression] + group_selects

    def _group_selects(self, group_by: list[str], event_table_alias: str) -> list[str]:
        selects = []

        for key in group_by:
            if key in CORE_FIELDS:
                selects.append(f"{event_table_alias}.{key} AS {key}")
            else:
                selects.append(f"val_{key}.value AS {key}")

        return selects

    def _props_join_expression(self, event_name: str, alias: str, key: str):
        """Return LEFT JOIN clause for a specific property key."""

        return (
            f"LEFT JOIN {self._event_props_table_name(event_name)} AS {alias} "
            f"ON e.event_id = {alias}.event_id AND {alias}.key = '{key}'"
        )

    def _group_props_join_expression(
        self, event_name: str, group_by: list[str]
    ) -> list[str]:
        joins = []

        for key in group_by:
            if key not in CORE_FIELDS:
                alias = f"val_{key}"
                joins.append(self._props_join_expression(event_name, alias, key))

        return joins

    def _wheres_and_joins(
        self, event_name: str, filters: dict[str, str] | None
    ) -> tuple[list[str], list[str]]:
        """Generate SQL WHERE snippets and JOIN clauses for filters."""
        filters = filters or {}
        joins = []
        wheres = []

        for key, value in filters.items():
            if key in CORE_FIELDS:
                wheres.append(f"e.{key} = '{value}'")
            else:
                alias = f"f_{key}"
                joins.append(self._props_join_expression(event_name, alias, key))
                wheres.append(f"{alias}.value = '{value}'")

        return wheres, joins

    def _interval_sql(self, interval_str: str) -> str:
        """Convert a simple interval string (e.g. '7d', '24h', '1w') to BigQuery INTERVAL SQL."""
        m = re.fullmatch(r"(\d+)([hdw])", interval_str.strip().lower())

        if not m:
            raise ValueError(
                f"Invalid interval format: {interval_str}. Use forms like '7d', '24h', '1w'"
            )

        qty, unit = m.groups()

        unit_sql = UNIT_SQL_MAP[unit]

        return f"INTERVAL {qty} {unit_sql}"
