### Segments API (/api/v1/segments)

Segments define rule-based cohorts used for targeting.

Common requirements:

- Bearer token and app context.

#### POST /api/v1/segments/

Create a segment.

Request

```json
{
	"name": "High Value Users",
	"description": "Users with LTV > 1000",
	"rule_config": {
		"operator": "AND",
		"conditions": [{ "field": "ltv", "operator": ">", "value": 1000 }]
	}
}
```

Response

```json
{ "pid": "<uuid>", "name": "High Value Users", "description": "Users with LTV > 1000", "rule_config": { ... } }
```

#### GET /api/v1/segments/

List segments.

Query params

- search: string (optional)
- skip: int
- limit: int

Response

```json
[
  { "pid": "<uuid>", "name": "High Value Users", "description": "...", "rule_config": { ... } }
]
```

#### GET /api/v1/segments/{segment_pid}/

Get a segment with linked personalisations.

Response

```json
{
  "pid": "<uuid>",
  "name": "High Value Users",
  "description": "...",
  "rule_config": { ... },
  "personalisations": [ { "personalisation": { "pid": "<uuid>", "name": "Promo 10%" } } ]
}
```

#### PUT /api/v1/segments/{segment_pid}/

Update a segment.

Request (any subset)

```json
{
	"name": "VIP Users",
	"description": "Updated",
	"rule_config": { "conditions": [], "operator": "AND" }
}
```

Response: updated segment object.
