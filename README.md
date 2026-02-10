## PaygOps Community Edition

PaygOps Community Edition is the open‑source version of the PaygOps platform: a modular loan management platform and CRM/ERP designed for off‑grid and distributed asset financing operations. It provides client and portfolio management, loan management, payments, stock management, messaging, reporting, and integrations with devices for PAYGO. 

---

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

- **OpenPAYGO API base URL** (used in the Device API settings, e.g. `http://openpaygo:5001/` depending on the OpenPAYGO configuration).
- **The same `API_BEARER_TOKEN`** value, entered in the Device API configuration.

#### 3. Configure the Device API in PaygOps

Once both stacks are running:

1. Sign in to the PaygOps web app (default: `http://localhost:8000/`).
2. Go to **Settings → Advanced settings**.
3. Locate the **Device Integration Settings** configuration section.
4. Click the **Add New Integration** button
5. Set:
   - **Device Code** to `OPT` 
   - **Device Name** to `OpenPAYGO`
   - **Device API Type** to `One Way Device Code`
   - **Device API Version** to `v2`
   - **Offline Mode**, **Pairing** and **Usage Metrics** to `Disabled` (it is possible with OpenPAYGO but not currently supported by the OpenPAYGO Docker container)
   - **Supports Offer Type** to `Time Based` (usage based is also possible with OpenPAYGO but not currently supported by the OpenPAYGO Docker container)
   - **Device API URL** to the internal OpenPAYGO URL, for example `http://openpaygo:5001/` (adjust the port and path if your OpenPAYGO container uses a different one).
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

### User documentation (Doc360)

End‑user and functional documentation for PaygOps is maintained in the **PaygOps Doc360** portal. Contact your PaygOps representative or administrator to obtain access credentials. 
Video trainings are available online and accessible from PaygOps web app.

---

## Codebase Structure

See [Codebase Structure](codebase_structure.md) for details on PaygOps' frameworks and libraries, folder structure, and and testing tools.

---

## Contributing

Please read our [Contributing Guidelines](CONTRIBUTING.md) for details on how to contribute to this project.

---

## License

This project is licensed under the terms described in our [License](LICENSE.md).  
Please read that file carefully before deploying PaygOps Community in production or redistributing modified versions.


