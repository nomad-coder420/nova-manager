### Recommendations API (/api/v1/recommendations)

Generate AI-powered experience recommendations using current context.

Common requirements:

- Bearer token and app context.

#### POST /api/v1/recommendations/get-ai-recommendations/

Generate a recommendation based on user prompt and current experiences context.

Request

```json
{ "user_prompt": "Improve conversion on homepage" }
```

Response

```json
{
	"pid": "<uuid>",
	"experience_id": "<uuid>",
	"personalisation_data": {
		"experience_name": "Homepage",
		"reason": "Button color change"
	}
}
```

#### GET /api/v1/recommendations/

List generated recommendations.

Response

```json
[
  { "pid": "<uuid>", "experience_id": "<uuid>", "personalisation_data": { ... } }
]
```
