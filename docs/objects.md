### Objects API (/api/v1/feature-flags)

Objects represent feature flags and their default variants. They can be synced from client-side object definitions.

Common requirements:

- Most endpoints require Bearer token and app context.

#### POST /api/v1/feature-flags/sync-nova-objects/

Sync Nova objects and experiences from a client-side registry.

Request

```json
{
	"organisation_id": "org-123",
	"app_id": "app-123",
	"objects": {
		"Button": {
			"type": "ui",
			"keys": {
				"text": {
					"type": "string",
					"description": "Button text",
					"default": "Buy"
				},
				"color": {
					"type": "string",
					"description": "CSS color",
					"default": "#000"
				}
			}
		}
	},
	"experiences": {
		"Homepage": { "description": "Home screen", "objects": { "Button": true } }
	}
}
```

Response

```json
{
	"success": true,
	"objects_processed": 1,
	"objects_created": 1,
	"objects_updated": 0,
	"objects_skipped": 0,
	"experiences_processed": 1,
	"experiences_created": 1,
	"experiences_updated": 0,
	"experiences_skipped": 0,
	"experience_features_created": 1,
	"dashboard_url": "https://dashboard.nova.com/objects",
	"message": "Processed 1 objects and 1 experiences successfully",
	"details": [
		{
			"object_name": "Button",
			"action": "created",
			"flag_id": "<uuid>",
			"message": "Created feature flag with default variant"
		}
	]
}
```

#### GET /api/v1/feature-flags/

List feature flags.

Query params

- active_only: boolean (default false)
- skip: int (default 0)
- limit: int (default 100)

Response

```json
[
	{
		"pid": "<uuid>",
		"name": "Button",
		"description": "UI button",
		"type": "ui",
		"is_active": true,
		"keys_config": {
			"text": {
				"type": "string",
				"description": "Button text",
				"default": "Buy"
			}
		},
		"default_variant": { "text": "Buy", "color": "#000" },
		"experiences": [{ "experience_id": "<uuid>" }]
	}
]
```

#### GET /api/v1/feature-flags/available/

List feature flags not assigned to any experience.

Response: same shape as list.

#### GET /api/v1/feature-flags/{flag_pid}/

Get detailed feature flag with linked experiences.

Response

```json
{
	"pid": "<uuid>",
	"name": "Button",
	"description": "UI button",
	"type": "ui",
	"is_active": true,
	"keys_config": {
		"text": { "type": "string", "description": "Button text", "default": "Buy" }
	},
	"default_variant": { "text": "Buy", "color": "#000" },
	"experiences": [{ "experience": { "pid": "<uuid>", "name": "Homepage" } }]
}
```
