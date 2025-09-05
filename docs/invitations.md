### Invitations API (/api/v1/invitations)

Invite users to join your organisation with roles.

Common requirements:

- Bearer token, app context, and admin/owner role for protected endpoints.

#### POST /api/v1/invitations/invite

Send an invitation (admin/owner only).

Request

```json
{ "email": "new.user@example.com", "role": "ADMIN" }
```

Response

```json
{
	"id": "<uuid>",
	"email": "new.user@example.com",
	"role": "ADMIN",
	"status": "pending",
	"expires_at": "2024-01-02T00:00:00Z",
	"invited_by_name": "Jane",
	"organisation_name": "Acme",
	"created_at": "2024-01-01T00:00:00Z"
}
```

#### GET /api/v1/invitations/invitations

List invitations for the organisation (admin/owner only).

Query params

- status: pending | accepted | cancelled | all (default pending)

Response

```json
[
	{
		"id": "<uuid>",
		"email": "new.user@example.com",
		"role": "ADMIN",
		"status": "pending",
		"expires_at": "2024-01-02T00:00:00Z",
		"invited_by_name": "Jane",
		"created_at": "2024-01-01T00:00:00Z"
	}
]
```

#### DELETE /api/v1/invitations/invitations/{invitation_id}

Cancel an invitation (admin/owner only).

Response

```json
{ "message": "Invitation cancelled successfully" }
```

#### GET /api/v1/invitations/validate-invite/{token}

Validate an invitation token (public endpoint).

Response

```json
{
	"valid": true,
	"organisation_name": "Acme",
	"invited_by_name": "Jane",
	"role": "ADMIN",
	"email": "new.user@example.com"
}
```
