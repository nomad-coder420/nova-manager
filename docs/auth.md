### Auth API (/api/v1/auth)

Handles user registration, login, token refresh, and app management.

Common requirements:

- Bearer token required for all except `register`, `login`, and `refresh` (uses refresh token body).
- Organisation context required for app creation/listing/switching unless otherwise noted.

#### POST /api/v1/auth/register

Register a new user. If `invite_token` is present, company is ignored; otherwise `company` is required.

Request

```json
{
	"email": "jane@example.com",
	"password": "secret123",
	"name": "Jane Doe",
	"invite_token": null,
	"company": "Acme Inc"
}
```

Response

```json
{
	"access_token": "<JWT>",
	"refresh_token": "<JWT>",
	"token_type": "bearer",
	"expires_in": 3600
}
```

#### POST /api/v1/auth/login

Login with email and password.

Request

```json
{ "email": "jane@example.com", "password": "secret123" }
```

Response: same as register.

#### POST /api/v1/auth/refresh

Exchange a refresh token for a new access token.

Request

```json
{ "refresh_token": "<refresh_jwt>" }
```

Response

```json
{
	"access_token": "<JWT>",
	"refresh_token": "<refresh_jwt>",
	"token_type": "bearer",
	"expires_in": 3600
}
```

#### GET /api/v1/auth/me

Get current user info.

Headers

- Authorization: Bearer <access_token>

Response

```json
{
	"name": "Jane Doe",
	"email": "jane@example.com",
	"has_apps": true,
	"role": "OWNER"
}
```

#### POST /api/v1/auth/apps

Create a new app and receive new tokens bound to that app context.

Headers

- Authorization: Bearer <access_token> (organisation context required)

Request

```json
{ "name": "My App", "description": "Demo app" }
```

Response

```json
{
	"app": {
		"id": "<uuid>",
		"name": "My App",
		"description": "Demo app",
		"created_at": "2024-01-01T00:00:00Z"
	},
	"access_token": "<JWT>",
	"refresh_token": "<JWT>",
	"token_type": "bearer",
	"expires_in": 3600
}
```

#### GET /api/v1/auth/apps

List apps for the organisation.

Headers

- Authorization: Bearer <access_token> (organisation context required)

Response

```json
[
	{
		"id": "<uuid>",
		"name": "My App",
		"description": "Demo",
		"created_at": "2024-01-01T00:00:00Z"
	}
]
```

#### POST /api/v1/auth/switch-app

Switch the current app context; returns new tokens.

Headers

- Authorization: Bearer <access_token> (organisation context required)

Request

```json
{ "app_id": "<uuid>" }
```

Response: same shape as token response.
