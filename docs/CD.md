# Continuous Deployment

Every published GitHub release builds a Docker image and pushes it to the
GitHub Container Registry (GHCR). A Portainer webhook is then called so the
running Swarm service pulls the new image and restarts automatically — no
manual intervention needed on the host.

```
release published ──> build & push image to GHCR ──> call Portainer webhook ──> service updates
```

This document explains how to set up the Docker Swarm / Portainer side once,
so future releases deploy themselves.

## Architecture

- **Configuration**: Non-sensitive settings live in `config/config.json` (checked
  into git). Sensitive credentials come from environment variables.
- **Secrets**: Bot token, API keys, and database credentials are passed as
  environment variables or Docker secrets.
- **Database**: MySQL/MariaDB credentials are injected via environment variables,
  not hardcoded in config.

## 1. How the image is built

[`.github/workflows/cd.yml`](../.github/workflows/cd.yml) builds the image
from the repo's [`Dockerfile`](../Dockerfile) for **both amd64 and arm64**
(multiarch) and pushes it to:

```
ghcr.io/bishoko/bishokus:<release-tag>
ghcr.io/bishoko/bishokus:latest
```

(owner/repo lowercased, e.g. `ghcr.io/bishoko/bishokus:latest`).

The same image tag works on both x86-64 and ARM64 architectures (e.g., Raspberry Pi,
Mac M1/M2/M3, AWS Graviton). Docker automatically selects the correct variant
based on your host's architecture.

No extra secret is required for this step — it authenticates with the
built-in `GITHUB_TOKEN`, which is granted `packages: write` at the job level.

By default, packages published this way are **private**. Either:

- Make the package public (GitHub → your profile/org → **Packages** →
  `bishokus` → **Package settings** → **Change visibility** → Public), which
  lets any Swarm node pull it without credentials, **or**
- Keep it private and configure a registry in Portainer (see step 3) so it
  injects pull credentials for you.

## 2. Deploy the stack

On your Swarm cluster (via Portainer → **Stacks** → **Add stack**), deploy
something like:

```yaml
version: "3.8"

services:
  bishokus:
    image: ghcr.io/bishoko/bishokus:latest
    environment:
      TZ: Europe/Paris
      BOT_TOKEN: ${BOT_TOKEN}
      DB_HOST: ${DB_HOST:-mysql}
      DB_PORT: ${DB_PORT:-3306}
      DB_USER: ${DB_USER:-bishokus}
      DB_PASSWORD: ${DB_PASSWORD}
      DB_NAME: ${DB_NAME:-bishokus}
      TEST_BOT_TOKEN: ${TEST_BOT_TOKEN:-}
      OPENWEATHER_API_KEY: ${OPENWEATHER_API_KEY:-}
      BLAGUES_API_KEY: ${BLAGUES_API_KEY:-}
    secrets:
      - source: bishokus_config
        target: /app/config/config.json
        mode: 0444
    volumes:
      - bishokus_logs:/app/.logs
    networks:
      - bishokus_net
    deploy:
      replicas: 1
      restart_policy:
        condition: any
        delay: 5s
      update_config:
        order: stop-first

networks:
  bishokus_net:
    driver: overlay

volumes:
  bishokus_logs:

secrets:
  bishokus_config:
    external: true
```

### Environment variables

The following **sensitive** environment variables must be provided by Portainer
or Docker Compose:

- `BOT_TOKEN` — Discord bot token (required)
- `DB_PASSWORD` — Database password (required unless DB is running without auth)
- `TEST_BOT_TOKEN` — Test bot token (optional)
- `OPENWEATHER_API_KEY` — OpenWeather API key (optional)
- `BLAGUES_API_KEY` — Blagues API key (optional)

The following database variables can be overridden (defaults shown):

- `DB_HOST` — Database host (`mysql` if running as a Swarm service; `localhost`
  for local dev)
- `DB_PORT` — Database port (default: `3306`)
- `DB_USER` — Database user (default: `bishokus`)
- `DB_NAME` — Database name (default: `bishokus`)

#### Passing environment variables in Portainer

In **Stacks**, edit the stack (or during creation) and add these under the
service's **environment** section — either as literal values or using
`${VAR_NAME}` syntax to reference Portainer environment variables.

Alternatively, you can define these in a `.env` file in the Portainer stack
directory.

### The config secret

`config/config.json` contains only **non-sensitive** application settings:
URLs, IDs, user preferences, etc. It is provided as a Docker secret so it can
be updated without rebuilding the image.

Create it once:

1. Portainer → **Secrets** → **Add secret** → name it `bishokus_config`.
2. Paste the contents of `config/config.example.json` (from the repo).
3. Adjust any Discord IDs, URLs, or preferences as needed.
4. Save.

The secret is automatically mounted at `/app/config/config.json` (read-only)
in all running containers.

### Database setup

**Option A: External managed MySQL/MariaDB**

If your database runs outside Docker (e.g., on the host or a separate server),
set `DB_HOST` to its IP/hostname and provide `DB_PASSWORD` via environment
variables.

**Option B: MySQL container on the same Swarm**

Deploy MySQL as a separate Swarm service and attach both to the same overlay
network. Example:

```yaml
mysql:
  image: mariadb:11
  environment:
    MARIADB_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
    MARIADB_DATABASE: bishokus
    MARIADB_USER: bishokus
    MARIADB_PASSWORD: ${MYSQL_BISHOKUS_PASSWORD}
  volumes:
    - mysql_data:/var/lib/mysql
  networks:
    - bishokus_net
  deploy:
    replicas: 1

bishokus:
  image: ghcr.io/bishoko/bishokus:latest
  environment:
    DB_HOST: mysql  # Swarm's service name discovery
    DB_USER: bishokus
    DB_PASSWORD: ${MYSQL_BISHOKUS_PASSWORD}
    # ... other vars ...
  networks:
    - bishokus_net
  depends_on:
    - mysql

volumes:
  mysql_data:
```

**Option C: Managed database (CloudSQL, RDS, etc.)**

Use the managed service's external IP, DNS name, or proxy endpoint. The bot
connects like it would to any external database — just set `DB_HOST` and
provide credentials via environment variables.

### Logs

`.logs` is kept on a named volume so logs survive container restarts. Logs are
written to the container's `/app/.logs` directory with names like
`YYYY-MM-DD-bishokus.log`. To disable persistence, drop the `volumes` entry.

## 3. (Optional) Add a registry for private packages

If you kept the GHCR package private, add it as a registry so Portainer can
authenticate pulls on your behalf:

1. Portainer → **Registries** → **Add registry** → **Custom registry**.
2. URL: `ghcr.io`.
3. Username: your GitHub username. Password: a GitHub **Personal Access
   Token** with `read:packages` scope.
4. Save, then make sure this registry is available to the environment/stack
   you deployed.

## 4. Wire up the webhook

This is what makes deployment automatic on release:

1. In Portainer, open the `bishokus` service (Stacks → your stack →
   `bishokus`, or Services → `bishokus`).
2. On the service detail page, enable **Webhook**. Portainer generates a URL
   like `https://<portainer-host>/api/webhooks/<uuid>`.
3. Copy that URL and add it as a GitHub Actions secret named
   `PORTAINER_WEBHOOK_URL` (repo → **Settings** → **Secrets and variables** →
   **Actions** → **New repository secret**).

Calling this webhook makes Portainer run the Swarm-native "force update"
trick (`docker service update` against the same `:latest` tag), which makes
Swarm re-resolve the tag to its latest digest and roll the service — i.e. the
new image is pulled and the container restarted, with no SSH access to the
host required.

## 5. Development

For local development, create a `.env` file in the repo root with your secrets:

```bash
cp .env.example .env
# Edit .env and fill in your local values
BOT_TOKEN=your_local_bot_token
DB_HOST=localhost
DB_USER=bishokus
DB_PASSWORD=your_local_db_password
```

The `bot.py` script will load this automatically.
**Never commit `.env`** — it's in `.gitignore`.

## 6. System dependencies

The Docker image includes `ffmpeg` and `ffprobe`, which are required for the
`!gif` command (video-to-GIF conversion) for example. These are pre-installed in the image
and require no extra configuration.

If running the bot outside Docker, ensure ffmpeg is installed on the host:

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
choco install ffmpeg
```
