#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
chmod +x ./*.sh || true

./auth.sh || true
./users.sh || true
./objects.sh || true
./experiences.sh || true
./segments.sh || true
./metrics.sh || true
./personalisations.sh || true
./events.sh || true
./evaluation.sh || true
./invitations.sh || true
./recommendations.sh || true

echo "Done." 