### Evaluation API (/api/v1/user-experience)

Runtime endpoints to evaluate and return experience assignments for users.

Common requirements:

- No auth dependency is enforced in code for these endpoints; include required organisation/app/user IDs in the body.
- The user must exist; otherwise 404 is returned by the flow.

#### POST /api/v1/user-experience/get-experience/

Get assignment for a single experience.

Request

```json
{
	"organisation_id": "org-123",
	"app_id": "app-123",
	"user_id": "external-user-123",
	"experience_name": "Homepage",
	"payload": { "country": "US", "ltv": 1200 }
}
```

Response

```json
{
	"experience_id": "<uuid>",
	"personalisation_id": "<uuid>|null",
	"personalisation_name": "Promo 10%|null",
	"experience_variant_id": "<uuid>|null",
	"features": {
		"Button": {
			"feature_id": "<uuid>",
			"feature_name": "Button",
			"variant_id": "<uuid>|null",
			"variant_name": "Blue Button|default",
			"config": { "color": "#00F" }
		}
	},
	"evaluation_reason": "personalisation_match|default_experience|no_experience_assignment_error|no_personalisation_match_error"
}
```

#### POST /api/v1/user-experience/get-experiences/

Get assignments for multiple named experiences.

Request

```json
{
	"organisation_id": "org-123",
	"app_id": "app-123",
	"user_id": "external-user-123",
	"payload": { "country": "US" },
	"experience_names": ["Homepage", "Checkout"]
}
```

Response

```json
{
  "Homepage": { "experience_id": "<uuid>", "features": { ... }, "evaluation_reason": "personalisation_match" },
  "Checkout": { "experience_id": "<uuid>", "features": { ... }, "evaluation_reason": "default_experience" }
}
```

#### POST /api/v1/user-experience/get-all-experiences/

Get assignments for all active features/objects across experiences for a user.

Request: same as get-experiences without `experience_names`.

Response: map keyed by experience name.

Notes

- If the user doesn’t exist, a 404 is returned. Create or update the user first via Users API.
