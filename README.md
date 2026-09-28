## PaygOps Community Edition

PaygOps Community Edition is the open‑source version of the PaygOps platform: a modular loan management platform and CRM/ERP designed for off‑grid and distributed asset financing operations. It provides client and portfolio management, loan management, payments, stock management, messaging, reporting, and integrations with devices for PAYGO. 


## Deploy to managed hosting

To deploy PaygOps and the required dependant services (database, etc.) to a hosting provider, just click the button below for your preffered supported provider and follow the steps. If you know of other providers that support one click deployment and would like to add them feel free to create a request or contribute it yourself. 

[![Deploy to DigitalOcean](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/MasungaTech/PaygOps-Community-OneClick/tree/main)



## Using PaygOps

### Getting started (local development with Docker)

- **Prerequisites**
  - **Docker** and **Docker Compose** installed.
  - At least **4 GB RAM** available for Docker.

- **Clone and start**

```bash
git clone <this-repo-url> paygops-community
cd paygops-community

# Build images and start all services
docker compose up --build
```

- **What this starts**
  - **PostgreSQL** on `localhost:5432` (database `main_db`).
  - **Redis** on `localhost:6379`.
  - **Web application** (browser UI) on `http://localhost:8000/`.
  - **Public API** on `http://localhost:6789/`.
  - **Background workers** (Celery worker and beat) for asynchronous tasks.
  - **PostgreSQL analytical db** on `localhost:5433`.

The first startup may take several minutes while the database is created and migrations are applied (handled by the `auto_setup` service).

To stop the stack:

```bash
docker compose down
```

- **Log into PaygOps**

Open the web application `http://localhost:8000` and log in with the credentials defined by the environment variables `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD`, see [below](#environment-variables-to-set).


### Environment variables to set

Most configuration is read from environment variables defined in `config.py` and used across the codebase.  
The provided `docker-compose.yml` includes safe defaults for **local development only**. For production you must override them.

- **Core environment**
  - **`ENV_VAR`**: environment type, one of `DEV`, `TEST`, `PROD`.  
    - Local default in compose: `DEV`. Should be set to `PROD` in production. 
  -  **`PAYG_URL`**: base URL of the PaygOps instance, used to build external links and instance metadata.

- **Database & cache**
  - **`PG_HOST`**: PostgreSQL host (default: `postgres` inside Docker).
  - **`PG_PORT`**: PostgreSQL port (default: `5432`).
  - **`PG_USER`**: PostgreSQL user (default: `solaris_deploy` in the example compose).
  - **`PG_PASSWORD`**: PostgreSQL password (**must be set in production**).
  - **`REDIS_SERVER_ADDRESS`**: Redis host (default: `redis` inside Docker).
  - **`REMOTE_ADB_ADDRESS`**, **`ANALYTICAL_DB_HOST`**, **`DISABLE_ANALYTICAL_DB`**: control analytical database usage (disabled by default in the example compose).

- **Runtime & scaling**
  - **`GLOBAL_SCALE`**: base concurrency/worker scale (integer, see `entrypoint.sh`).

- **Security & identity**
  - **`SECRET_KEY`**: application secret key for signing sessions and API tokens.  
    - **Required in production**.  
    - The example compose sets `SECRET_KEY="change-me-in-production"` – you **must change this**.
  - **`DEFAULT_PASSWORD_COMMUNICATION`**: preferred channel for password communication (`email` or `sms`).
  - **`INITIAL_ADMIN_EMAIL`** and **`INITIAL_ADMIN_PASSWORD`**: credentials for the first admin user created by the `auto_setup` process.  
    - In development, example values are provided in `example_secrets.env`.  
    - In production, set these to a secure email/password pair

- **Email delivery**
  - **`SENDER_EMAIL`**: email address used in the `From` header for system emails (default: `donotreply@example.com`).
  - **`EMAIL_SERVER_URL`**: SMTP server hostname
  - **`EMAIL_SERVER_USER`**: SMTP username
  - **`EMAIL_SERVER_PASSWORD`**: SMTP password(must be set to a valid credential for your email provider).

- **External URLs & integrations**
  - **`SUPPORT_EMAIL`**, **`SUPPORT_URL`**: contact points displayed in the UI and emails.
  - **`ANTHROPIC_API_KEY`**: key for AI‑powered features (if enabled).
  - **`GOOGLE_MAPS_API_KEY`**, **`GOOGLE_CAPTCHA_SITE_KEY`**: Google Maps and reCAPTCHA integration keys.
  - **`LOGIN_OAUTH_URL`**, **`LOGIN_JWT_SECRET`**: configuration for an external login platform / SSO.

### Example env file for local development

For local development, we provide an `example_secrets.env` file next to `docker-compose.yml`.  
This file is referenced by `docker-compose.yml` via `env_file` and contains **example values only**:

- Database credentials: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `PG_USER`, `PG_PASSWORD`
- Core environment: `ENV_VAR`, `PAYG_URL`
- Initial admin credentials: `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD`
- Email configuration: `SENDER_EMAIL`, `EMAIL_SERVER_URL`, `EMAIL_SERVER_USER`, `EMAIL_SERVER_PASSWORD`
- Security: `SECRET_KEY`

Before running in production, **do not use `example_secrets.env` as-is**:

- Copy it to your own file (for example `secrets.env`).
- Replace all example values with strong secrets and real URLs/emails.
- Point your production compose or deployment manifests to your secure env file instead.

### OpenPAYGO integration

To use OpenPAYGO enabled devices with PaygOps Community Edition, you can integrate PaygOps with an external OpenPAYGO API by running the [`MasungaTech/OpenPAYGO-Docker`](https://github.com/MasungaTech/OpenPAYGO-Docker) container alongside the stack and then pointing the **Device API** settings to it.

#### 1. Add the OpenPAYGO container to `docker-compose.yml`

The example Docker compose file is `docker-compose.yml` at the root, to run OpenPAYGO with it:

1. **Add an `openpaygo` service** to `docker-compose.yml` (values are examples; check the OpenPAYGO‑Docker README for the latest image name and variables):

   ```yaml
   services:
     # existing services (postgres, redis, auto_setup, web, api, celery_worker, celery_beat…)

     openpaygo:
       image: ghcr.io/masungatech/openpaygo-docker:latest  # or build from the OpenPAYGO-Docker repo
       container_name: openpaygo
       restart: unless-stopped
       ports:
         - "5001:8000"  # Expose container port 8000 on host port 5001 for device uploads
       environment:
         # MAKE ABSOLUTELY SURE to change these defaults in production
         API_BEARER_TOKEN: your-secure-api-token-here
         CSV_UPLOAD_USERNAME: admin
         CSV_UPLOAD_PASSWORD: your-secure-password
         DB_PROVIDER: postgres
         DB_HOST: openpaygo-db
         DB_USER: paygo_user
         DB_PASSWORD: verysecretpassword
         DB_NAME: openpaygo
       depends_on:
         - openpaygo-db

     openpaygo-db:
       image: postgres:16
       container_name: openpaygo_db
       restart: unless-stopped
       environment:
         POSTGRES_DB: openpaygo
         POSTGRES_USER: paygo_user
         POSTGRES_PASSWORD: verysecretpassword
       volumes:
         - openpaygo_db_data:/var/lib/postgresql/data

   volumes:
     # existing volumes…
     openpaygo_db_data:
   ```

On Linux environments, you also have to add this snippet for the containers `api`, `celery_worker` and `celery_worker_heavy` to be able to access `openpaygo` through docker networks:

```yaml
#    Needed on Linux only:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

An example compose file including both PaygOps Community and OpenPAYGO-Docker is provided in `docker-compose-openpaygo.yml`.

2. **Bring the stack up (or recreate it) with the new services**:

   ```docker compose up -d --build```

3. **Upload devices to the OpenPAYGO API as needed**:

Go to `http://localhost:5001/upload-devices` with the username and password setup in the environment variable and upload a CSV matching the standard OpenPAYGO CSV format including the devices you want to use and their information (serial number, secret key, etc.). 

#### 2. Environment variables for the integration

On the OpenPAYGO side, the key environment variables (see the OpenPAYGO‑Docker README for the authoritative list) typically include:

- **`DB_HOST`**, **`DB_USER`**, **`DB_PASSWORD`**, **`DB_NAME`**, **`DB_PROVIDER`**: database connection used by OpenPAYGO.
- **`API_BEARER_TOKEN`**: bearer token that clients (including PaygOps) must send when calling the OpenPAYGO API.

On the PaygOps side you usually only need:

- **OpenPAYGO API base URL** (used in the Device API settings, e.g. `http://host.docker.internal:5001/` depending on the OpenPAYGO configuration).
- **The same `API_BEARER_TOKEN`** value, entered in the Device API configuration.

#### 3. Configure the Device API in PaygOps

Once both stacks are running:

1. Sign in to the PaygOps web app (default: `http://localhost:8000/`).
2. Go to **Settings → Advanced settings**.
3. Locate the **Device Integration Settings** configuration section.
4. Click the **Add New Integration** button
5. Set:
   - **Device Code** to `LDC` (for "Local Device Cloud")
   - **Device Name** to `OpenPAYGO`
   - **Device API Type** to `One Way Device Code`
   - **Device API Version** to `v2`
   - **Offline Mode**, **Pairing** and **Usage Metrics** to `Disabled` (it is possible with OpenPAYGO but not currently supported by the OpenPAYGO Docker container)
   - **Supports Offer Type** to `Time Based` (usage based is also possible with OpenPAYGO but not currently supported by the OpenPAYGO Docker container)
   - **Device API URL** to the internal OpenPAYGO URL, for example `http://host.docker.internal:5001/` (adjust the port and path if your OpenPAYGO container uses a different one).
   - **Device API Key** to the same value as `API_BEARER_TOKEN` configured on the `openpaygo` container. 
6. Save the changes. New device operations that use the Device API will now be sent to the OpenPAYGO service.

### Deploying in production

The example `docker-compose.yml` is intentionally **minimal and development‑oriented**.  
For production you should:

- **Build a tagged image** from `Dockerfile`:

```bash
docker build -f Dockerfile -t paygops_community:<version> .
```

- **Run separate services** (web, API, workers, beat) with:
  - Managed **PostgreSQL** (or high‑availability cluster), for PaygOps (and for OpenPAYGO if you use it as well). 
  - Managed **Redis**.
  - A reverse proxy (e.g. **nginx**, Traefik) terminating TLS and routing to:
    - `web` service on port `8000`.
    - `api` service on port `6789` mapping to `/api/v1/`.
    - (Optionally, for device upload) `openpaygo` service on port 5001 mapping to `/openpaygo`

- **Run database setup and migrations** once at deploy time by invoking the container with `runtime_setup`:

```bash
docker run --rm \
  --env-file ./your-env-file.env \
  --network your-network \
  paygops_community:<version> \
  runtime_setup
```

- **Configure backups and monitoring** for PostgreSQL and Redis and set:
  - `PAYG_URL` to the public HTTPS URL of your instance.
  - Strong values for `SECRET_KEY`, database credentials, and any third‑party API keys.

### API documentation

PaygOps' API documentation is accessible from within the tool at `/admin/api_docs`, or at [API docs](https://apidocs.paygops.com/login/auto?login_as=22&parent_key=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJTb2xhcmlzIE9mZmdyaWQiLCJleHAiOjE3ODgzNDcwMDAsImlhdCI6MTc4ODM0MzQwMCwic3ViIjoiMiIsInBlcm1pc3Npb25zIjpbIkVkaXRJc3N1ZXMiLCJBZGRVc2VycyIsIkFzc2lnblJvbGVzIiwiVmlld0V4cGVuc2VzIiwiQW5zd2VyUHJvdGVjdGVkUXVlc3Rpb25Gb3JtcyIsIkVkaXRJbnRlcmFjdGlvbnMiLCJBZGRJbmNvbWluZ01lc3NhZ2VzIiwiVmlld0Rhc2hib2FyZHMiLCJFZGl0TGVhZHMiLCJTeW5jQ2xpZW50c01vYmlsZSIsIkluU3RvY2tWaWV3U3RvY2siLCJDb25maWd1cmVPcGVyYXRpb25hbEVudGl0aWVzQWRtaW4iLCJWaWV3VHJhbnNmZXJzIiwiR2l2ZUNvbW1pc3Npb25Ub0xlYWRHZW5lcmF0b3JzIiwiU3luY0ludGVyYWN0aW9uc01vYmlsZSIsIlZpZXdBc3NpZ25lZFRhc2tzIiwiTWFuYWdlQWxsQWNjb3VudHMiLCJFZGl0QXV0b21hdGlvbnMiLCJTeW5jTGVhZEdlbmVyYXRvcnNNb2JpbGUiLCJFZGl0UG9ydGZvbGlvTGVhZHMiLCJTeW5jT3duTGVhZEdlbmVyYXRvck1vYmlsZSIsIk1vdmVUb1Jlc3RyaWN0ZWRTdGF0dXNMZWFkcyIsIkZpbGxDdXN0b21Gb3Jtc0xlYWRzIiwiU3luY0FsbENyZWF0ZWRDbGllbnRzTW9iaWxlIiwiT3ZlcnJpZGVEZWxpdmVyeURhdGVMaW1pdHNMZWFkcyIsIkFwcHJvdmVUcmFuc2ZlcnMiLCJMaXN0UG9ydGZvbGlvcyIsIkVkaXRQbGFubmVkRGVsaXZlcnlEYXRlTGVhZHMiLCJFZGl0T2ZmZXJBd2FpdGluZ0RlbGl2ZXJ5TGVhZHMiLCJBUElDYWxsZXJBZG1pbiIsIlNlZUh1Yk5vdGlmaWNhdGlvbnNBZG1pbiIsIlN5bmNBbGxHZW5lcmF0ZWRMZWFkc01vYmlsZSIsIkFkZE5vdGVzRGV2aWNlcyIsIkRlbGV0ZU1vdmVTdG9jayIsIldpdGhDbGllbnRzVmlld1N0b2NrIiwiVmlld0FkZG9uT2ZmZXJzIiwiVmlld01lc3NhZ2VzIiwiVmlld0ludGVyYWN0aW9ucyIsIlZpZXdCYWRnZVRyYW5zZmVycyIsIkdpdmVEZWxheUFjdGlvbnMiLCJGaWxsQ3VzdG9tRm9ybXNDbGllbnRzIiwiRWRpdEh1YnMiLCJTeW5jQ29tcGxldGVkQ2xpZW50c01vYmlsZSIsIkRlbGV0ZUludGVyYWN0aW9ucyIsIkRvd25sb2FkR2xvYmFsQWNjb3VudHMiLCJFZGl0UmVnaW9ucyIsIkFkZFRhc2tzIiwiU3luY1BsYW5uaW5nTW9iaWxlIiwiRWRpdFRhZ3NEZXZpY2VzIiwiVG9PcnBoYW5lZE1vdmVTdG9jayIsIkFkZFBsYW5uaW5nIiwiRGVsZXRlQVBJSG9vayIsIkFkZEV4cGVuc2VzIiwiQ29uZmlndXJlTW9iaWxlQXBwU2V0dGluZ3NBZG1pbiIsIlNldENvbW1pc3Npb25MZWFkcyIsIkVkaXRJbnRlcmFjdGlvbnNTZXR0aW5nc0Zvcm1zIiwiRmlsbEN1c3RvbUZvcm1zVXNlckpvdXJuZXkiLCJBZGRQYXltZW50cyIsIkFkZE1vdmVTdG9jayIsIkRlbGV0ZVZpbGxhZ2VzIiwiRGVsZXRlUG9ydGZvbGlvcyIsIlBheUNsaWVudEFjdGlvbnMiLCJEZWxldGVUcmFuc2ZlcnMiLCJFZGl0Q2x1c3RlcnMiLCJNYW5hZ2VBY2NvdW50cyIsIkRlbGV0ZVBob25lTnVtYmVycyIsIkVkaXRVc2VySm91cm5leSIsIlRvSW5TdG9ja01vdmVTdG9jayIsIlN5bmNBbGxHZW5lcmF0ZWRDbGllbnRzTW9iaWxlIiwiQ29uZmlndXJlQXV0b21hdGlvbnNBZG1pbiIsIlZpZXdDbGllbnRzIiwiUnVuVXNlckpvdXJuZXkiLCJEZWxldGVDbHVzdGVycyIsIkVkaXRDbGllbnRzIiwiRGVsZXRlUGxhbm5pbmciLCJWaWV3Q3JlYXRlZExlYWRzIiwiRWRpdFJlc3RyaWN0ZWRQZXJzb25hbERldGFpbHNMZWFkcyIsIlN5bmNUYXNrQXNzaWduZWRUb01lTW9iaWxlIiwiR2l2ZVRva2Vuc09mZmxpbmVBY3Rpb25zIiwiQ29uZmlndXJlR2VuZXJhbFNldHRpbmdzQWRtaW4iLCJFZGl0Wm9uZXMiLCJBZGRJc3N1ZXMiLCJFZGl0U3ViVHlwZURldmljZXMiLCJDYW5jZWxDb250cmFjdEFjdGlvbnMiLCJWaWV3U2V0dGluZ3NJbnRlcmZhY2VBZG1pbiIsIkFkZENsaWVudEdyb3VwcyIsIlZpZXdMZWFkcyIsIkFkZEFzc2lnbmVkVGFza3MiLCJBZGRSZWdpb25zIiwiQ29uZmlndXJlVGFza1R5cGVBZG1pbiIsIkRlbGV0ZUZvcm1zIiwiTWFya0FzVW5EZWxpdmVyZWRBZGRPbnMiLCJWaWV3T2R5c3NleVBheW1lbnRzIiwiQ3JlYXRlQVBJVG9rZW5BZG1pbiIsIkVkaXRBZGRvbk9mZmVycyIsIlZpZXdBbGxNZXNzYWdlcyIsIkFkZFRhZ3NDbGllbnRzIiwiQ29sbGVjdENhc2hBY3Rpb25zIiwiRWRpdExlYWRHZW5lcmF0b3JzIiwiUmVxdWVzdFRyYW5zZmVycyIsIkFkZE91dGdvaW5nTWVzc2FnZXMiLCJEZWxldGVFeHBlbnNlcyIsIlZpZXdBY2NvdW50cyIsIkVkaXRJbnN0YWxsZWRMZWFkcyIsIlZpZXdCYWRnZUlzc3VlcyIsIkZyb21JblN0b2NrTW92ZVN0b2NrIiwiRGVsZXRlT3duTm90ZXNJc3N1ZXMiLCJBZGRIdWJzIiwiVW5kb0NvbnRyYWN0RGVmYXVsdGVkQWN0aW9ucyIsIldpdGhVc2Vyc1ZpZXdTdG9jayIsIlZpZXdPcnBoYW5lZFBheW1lbnRzIiwiVmlld0FjdGlvbnMiLCJBZGRSZXZlcnNlZFBheW1lbnRzIiwiQ3JlYXRlVGFnc0NsaWVudHMiLCJWaWV3VXNlcnMiLCJDb25maXJtVHJhbnNmZXJzIiwiRWRpdE90aGVyc0V4cGVuc2VzIiwiRWRpdEZvcm1zIiwiQWRkQVBJSG9vayIsIkFkZEZvcm1zIiwiQ3JlYXRlUm9sZXMiLCJWaWV3T3JwaGFuZWRQaG9uZU51bWJlcnMiLCJDb25maWd1cmVQYXltZW50Um91dGVyQWRtaW4iLCJEZWxldGVDcmVhdGVkVGFza3MiLCJPcnBoYW5lZFZpZXdTdG9jayIsIkNvbmZpZ3VyZUxvY2FsU2V0dGluZ3NBZG1pbiIsIkNvbmZpZ3VyZVBheW1lbnRNYW5hZ2VtZW50QWRtaW4iLCJWaWV3QWN0aXZpdHlMb2dBZG1pbiIsIlZpZXdQb3J0Zm9saW9zIiwiQ29uZmlndXJlQXV0b21hdGVkTWVzc2FnZXNBZG1pbiIsIkRlbGV0ZU5vdGVzRGV2aWNlcyIsIlN5bmNBbGxDcmVhdGVkTGVhZHNNb2JpbGUiLCJBZGRJbnRlcmFjdGlvbnMiLCJTeW5jSW5zdGFsbGVkTGFzdDJNb250aHNMZWFkc01vYmlsZSIsIkFkZEFkZG9uT2ZmZXJzIiwiVG9Mb3N0TW92ZVN0b2NrIiwiRWRpdEN1c3RvbVNNU0FkbWluIiwiU2VlQWxsTm90aWZpY2F0aW9uc0FkbWluIiwiQWRkWm9uZXMiLCJWaWV3SXNzdWVzIiwiTGlzdFVzZXJKb3VybmV5IiwiVmlld0F1dG9tYXRpb25zIiwiQXBwcm92ZUFkZE9ucyIsIkVkaXRPd25FeHBlbnNlcyIsIlZpZXdQYXlnb0RldmljZXMiLCJFZGl0QW1vdW50RXhwZW5zZXMiLCJWaWV3Um9sZXMiLCJFZGl0TG9hbk9mZmVycyIsIkVkaXRVc2VycyIsIlZpZXdCYWRnZUxlYWRzIiwiVmlld09ycGhhbmVkTWVzc2FnZXMiLCJWaWV3THVtcFN1bU9mZmVycyIsIlZpZXdGb3JtcyIsIlZpZXdHbG9iYWxEYXNoYm9hcmRzIiwiQWRkQ29udHJhY3RUZXJtc0NoYW5nZUFkZE9ucyIsIkNoYW5nZVBBWUdNb2RlRGV2aWNlcyIsIkNvbmZpZ3VyZUxhbmd1YWdlU2V0dGluZ3NBZG1pbiIsIkdvZ2xhRGFzaGJvYXJkcyIsIlN5bmNMZWFkc01vYmlsZSIsIkNoYW5nZVN0YXR1c09mQXNzaWduZWRUYXNrcyIsIkFkZFVzZXJKb3VybmV5IiwiR2l2ZURpc2NvdW50QWN0aW9ucyIsIkNvbmZpZ3VyZVBhY2thZ2VJbnN0YWxsZXJBZG1pbiIsIlZpZXdQYXltZW50cyIsIldpdGhNZVZpZXdTdG9jayIsIkFkZExvYW5PZmZlcnMiLCJEZWxldGVIdWJzIiwiRGVsZXRlRGV2aWNlcyIsIkVkaXRQbGFubmluZyIsIkRlbGV0ZVRhc2tzIiwiRXhwb3J0RGF0YUFkbWluIiwiQWRkVG9Db250cmFjdEFkZE9ucyIsIlZpZXdMZWFkR2VuZXJhdG9ycyIsIkZyb21XaXRoTWVNb3ZlU3RvY2siLCJTeW5jQWN0aXZhdGlvbkFjdGlvbnMiLCJFZGl0V2FsbGV0UGF5bWVudHMiLCJFZGl0Q2xpZW50TGVhZERhdGFTZXR0aW5nc0Zvcm1zIiwiQ3JlYXRlVGFnc0RldmljZXMiLCJEZWxldGVSZWdpb25zIiwiQ3JlYXRlUG9ydGZvbGlvcyIsIkVkaXRPZmZlcnMiLCJBZGRMZWFkcyIsIkNvbmZpZ3VyZVNhbGVzTWFuYWdlbWVudEFkbWluIiwiRWRpdEJhbm5lckFkbWluIiwiVmlld0xvYW5PZmZlcnMiLCJFZGl0UG9ydGZvbGlvQ2xpZW50cyIsIkdpdmVEZWxheU92ZXIyRGF5c0FjdGlvbnMiLCJWaWV3VGFza3MiLCJFZGl0T2ZmZXJQYXJ0aWFsbHlQYWlkTGVhZHMiLCJFZGl0Q2xpZW50R3JvdXBzIiwiQ29uZmlndXJlRGV2aWNlQVBJQWRtaW4iLCJBcHByb3ZlTGVhZHMiLCJSZW1vdmVMYXN0UGhvbmVOdW1iZXJzIiwiTWFya0FzRGVsaXZlcmVkV2l0aG91dFBsYW5uZWREYXRlQWRkT25zIiwiQWRkTm90ZXNJc3N1ZXMiLCJWaWV3QVBJRG9jdW1lbnRhdGlvbiIsIlZpZXdPd25MZWFkR2VuZXJhdG9ycyIsIkVkaXRNYWRlVHJhbnNmZXJzIiwiQ3VzdG9taXplUGxhdGZvcm1BZG1pbiIsIk1lcmdlQ2xpZW50cyIsIkRlbGV0ZVpvbmVzIiwiR2l2ZURpc2NvdW50T3ZlcjJEYXlzQWN0aW9ucyIsIkFkanVzdEJhbGFuY2VBbmRSZWNvbmNpbGVQYXltZW50cyIsIlZpZXdDdXN0b21CdXR0b25BY3Rpb25zIiwiQ29uZmlndXJlUGVyc29uYWxJbmZvQWRtaW4iLCJUb1VzZXJzTW92ZVN0b2NrIiwiTWFuYWdlUXVhbnRpdHlWaWV3U3RvY2siLCJDb25maWd1cmVTcGVjaWFsU2V0dGluZ3NBZG1pbiIsIlZpZXdCaWxsaW5nQWRtaW4iLCJGcm9tVXNlcnNNb3ZlU3RvY2siLCJEZWxldGVOb3Rlc0lzc3VlcyIsIkVkaXRBbGxvY2F0ZWREZXZpY2VMZWFkcyIsIkFkZENsdXN0ZXJzIiwiTWFya0FzRGVsaXZlcmVkQWRkT25zIiwiQWRkTWVzc2FnZXMiLCJUb1dpdGhNZU1vdmVTdG9jayIsIkVkaXRBY2NvdW50cyIsIkVkaXRQb3J0Zm9saW9zIiwiQWRkTGVhZEdlbmVyYXRvcnMiLCJWaWV3T3duVXNlcnMiLCJTeW5jSW5zdGFsbGVkTGFzdDEyTW9udGhzTGVhZHNNb2JpbGUiLCJEb0NoYW5nZU9mZmVyQWN0aW9ucyIsIk1hcmtDb250cmFjdERlZmF1bHRlZEFjdGlvbnMiLCJFZGl0VGFza3MiLCJNYWtlT25TdG9ja091dHNpZGVWaWV3QWN0aW9ucyIsIkZvcmNlUEFZR01vZGVEZXZpY2VzIiwiQWRkT2ZmZXJzIiwiQ2FuY2VsQWRkT25zIiwiVmlld09mZmVycyIsIlN5bmNJbnN0YWxsZWRMYXN0MldlZWtzTGVhZHNNb2JpbGUiLCJBZGRWaWxsYWdlcyIsIkVkaXRDcmVhdGVkVGFza3MiLCJBZGREZXZpY2VzIiwiQ29uZmlndXJlUHJvZHVjdEFkbWluIiwiQWRkTWFudWFsTWVzc2FnZXMiLCJQYWlyRGV2aWNlcyIsIkdpdmVOZWdhdGl2ZURpc2NvdW50VG9Db21wbGV0ZWRBY3Rpb25zIiwiVmlld0ZhdWx0c0xvZ3MiLCJIYW5kbGVSZXZlcnNlZFBheW1lbnRzIiwiQ2hhbmdlRXhwZWN0ZWRQYWlkQWN0aW9ucyIsIlN3YXBEZXZpY2VBY3Rpb25zIiwiTWVyZ2VMZWFkR2VuZXJhdG9ycyIsIlZpZXdQbGFubmluZyIsIkVkaXRFeHBlbnNlcyIsIkZyb21Mb3N0TW92ZVN0b2NrIiwiRGVSZWdpc3RlckFjdGlvbnMiLCJBZGRQdXJjaGFzaW5nQWRkT25zIiwiVmlld1JldmVyc2VkUGF5bWVudHMiLCJEZWxldGVDbGllbnRHcm91cHMiLCJGcm9tT3JwaGFuZWRNb3ZlU3RvY2siLCJSZWdpc3RlckFjdGlvbnMiLCJSZXN1bWVDb250cmFjdEFjdGlvbnMiLCJFZGl0VmlsbGFnZXMiLCJQYXVzZUNvbnRyYWN0QWN0aW9ucyIsIkVkaXRQbGFubmVkRGVsaXZlcnlEYXRlQWRkT25zIiwiVmlld0xvZ3MiLCJUZXN0UGVybWlzc2lvbiJdfQ.T1_eB_WBsVK8itZpw2cq-OajXadAjK7ZUX3MJDIVMuw).

### User documentation (Doc360)

End‑user and functional documentation for PaygOps is maintained in the **PaygOps Doc360** portal. Contact your PaygOps
representative or administrator to obtain access credentials for your instance. Alternatively, it can be accessed on 
[Doc360 on apidocs.paygops.com](https://apidocs.paygops.com/admin/doc360_login) (you may have to first open the API 
docs page linked in the previous section).
Video trainings are available online and accessible from PaygOps web app.


---

## Codebase Structure

See [Codebase Structure](codebase_structure.md) for details on PaygOps' frameworks and libraries, folder structure, and and testing tools.

---

## Community

PaygOps Community Edition is open source and open to contributions — fork it, test it, and help shape it.
- **Report issues**: Found a bug or have a feature request? [Open an issue](../../issues) on this repository.
- **Fork & contribute**: This repository is open to forks and pull requests. See [Contributing Guidelines](CONTRIBUTING.md) for guidelines.
- **Try it out**: A public test instance is available at [community-test.paygops.com](https://community-test.paygops.com) if you want to explore the platform before setting up your own. The documentation can be accessed at [Documentation360 on community-test](https://community-test.paygops.com/admin/doc360_login) and [API documentation on community-test](community-test.paygops.com/admin/api_docs).
- **Discord**: Join the [OSEA (Open Source Energy Access) community on Discord](https://discord.osea-community.org/) to chat with other users and contributors, ask questions, and follow ongoing development.

---

## License

This project is licensed under the terms described in our [License](LICENSE.md).  
Please read that file carefully before deploying PaygOps Community in production or redistributing modified versions.

---

## We're Using GitHub Under Protest

This project is currently hosted on GitHub.  This is not ideal; GitHub is a proprietary, trade-secret system that is not Free and Open Souce Software (FOSS). We invite you to read about the [Give up GitHub](https://GiveUpGitHub.org) campaign from [the Software Freedom Conservancy](https://sfconservancy.org) to understand some of the reasons why GitHub is not a good place to host FOSS projects.

Any use of this project's code by GitHub Copilot, past or present, is done without our permission.  We do not consent to GitHub's use of this project's code in Copilot.
