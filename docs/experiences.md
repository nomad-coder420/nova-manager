### Experiences API (/api/v1/experiences)

Experiences are groupings of feature flags (objects) and their variants.

Common requirements:

- Bearer token and app context.

#### GET /api/v1/experiences/

List experiences with filters and pagination.

Query params

- status: string (optional)
- search: string (optional)
- order_by: created_at | name | status (default created_at)
- order_direction: asc | desc (default desc)
- skip: int (default 0)
- limit: int (default 100)

Response

```json
[
	{
		"pid": "<uuid>",
		"name": "Homepage",
		"description": "Home screen",
		"status": "active",
		"variants": [{ "pid": "<uuid>" }],
		"features": [{ "pid": "<uuid>" }]
	}
]
```

#### GET /api/v1/experiences/{experience_pid}/

Get an experience with full details.

Response

```json
{
	"pid": "<uuid>",
	"name": "Homepage",
	"description": "Home screen",
	"status": "active",
	"features": [
		{
			"pid": "<uuid>",
			"feature_flag": {
				"pid": "<uuid>",
				"name": "Button",
				"description": "UI button",
				"type": "ui",
				"is_active": true,
				"keys_config": {},
				"default_variant": {}
			}
		}
	],
	"variants": [
		{
			"pid": "<uuid>",
			"name": "Variant A",
			"description": "Primary",
			"is_default": false,
			"last_updated_at": "2024-01-01T00:00:00Z",
			"feature_variants": [
				{
					"experience_feature_id": "<uuid>",
					"name": "Blue Button",
					"config": { "color": "#00F" }
				}
			]
		}
	]
}
```

#### GET /api/v1/experiences/{experience_pid}/features/

Get features attached to an experience.

Response

```json
[{ "pid": "<uuid>", "feature_flag": { "pid": "<uuid>", "name": "Button" } }]
```
