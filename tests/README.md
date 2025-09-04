# API Test Scripts

These curl-based scripts exercise each public API. They source a local `.env` for configuration.

Setup

- Copy `.env.example` to `.env` and fill values (BASE_URL, ORG_ID, APP_ID, ACCESS_TOKEN, etc.)
- Install `jq` for JSON parsing (brew install jq)
- Make scripts executable: `chmod +x *.sh`

Run

- `./auth.sh`
- `./objects.sh`
- `./experiences.sh`
- `./segments.sh`
- `./metrics.sh`
- `./personalisations.sh`
- `./events.sh`
- `./evaluation.sh`
- `./users.sh`
- `./invitations.sh`
- `./recommendations.sh`

Notes

- Some endpoints require valid data to exist (e.g., experiences, metrics). Scripts attempt to discover IDs via prior list calls.
- Personalisation creation has strict validation and may fail if your DB is not seeded accordingly.
