### Users API (/api/v1/users)

Manage Nova user records synchronized with your external user IDs.

#### POST /api/v1/users/create-user/

Create user if not exists, otherwise updates profile.

Request

```json
{
	"user_id": "external-user-123",
	"organisation_id": "org-123",
	"app_id": "app-123",
	"user_profile": { "country": "US", "ltv": 1200 }
}
```

Response

```json
{ "nova_user_id": "<uuid>" }
```

#### POST /api/v1/users/update-user-profile/

Update a user profile (or create if not exists).

Request

```json
{
	"user_id": "external-user-123",
	"organisation_id": "org-123",
	"app_id": "app-123",
	"user_profile": { "country": "US", "ltv": 1300 }
}
```

Response: same as create-user.
