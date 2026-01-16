## PaygOps Community Edition

PaygOps Community Edition is the open‑source version of Masunga's PaygOps platform: a modular loan management and CRM/ERP solution designed for off‑grid and distributed asset-finance operations. It provides core tools for client and portfolio management, loan management, payments, stock management, messaging, reporting, and integrations with PAYGO devices. 

For organisations looking for additional advanced features, cloud hosting, and dedicated support, PaygOps is also available as a SaaS solution through our commercial plans. These include capabilities such as advanced analytics, automations, mobile agent apps with offline capability, no-code UI editor, and more. For more information, visit [www.paygops.com](www.paygops.com) and explore the Premium and Microservices Offering.

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

The first startup may take several minutes while the database is created and migrations are applied (handled by the `auto_setup` service).

To stop the stack:

```bash
docker compose down
```

### Environment variables to set

Most configuration is read from environment variables defined in `config.py` and used across the codebase.  
The provided `docker-compose.yml` includes safe defaults for **local development only**. For production you must override them.

- **Core environment**
  - **`ENV_VAR`**: environment type, one of `DEV`, `TEST`, `PROD`.  
    - Local default in compose: `DEV`. Should be set to `PROD` in production. 
  -  **`PAYG_URL`**: base URL of the PaygOps instance, used to build external links and instance metadata.
  -  **`PAYG_API_URL`** (optional): base URL of the API, in development set it to the proper location of the API container (e.g. `http://localhost:6789`)

- **Database & cache**
  - **`PG_HOST`**: PostgreSQL host (default: `postgres` inside Docker).
  - **`PG_PORT`**: PostgreSQL port (default: `5432`).
  - **`PG_USER`**: PostgreSQL user (default: `solaris_deploy` in the example compose).
  - **`PG_PASSWORD`**: PostgreSQL password (**must be set in production**).
  - **`REDIS_SERVER_ADDRESS`**: Redis host (default: `redis` inside Docker).
  - **`REMOTE_ADB_ADDRESS`**, **`DISABLE_ANALYTICAL_DB`**: control analytical database usage (disabled by default in the example compose). Note that the Analytical DB must be in another database and is required for CSV exports as well. 

- **Runtime & scaling**
  - **`GLOBAL_SCALE`**: base concurrency/worker scale (integer, see `entrypoint.sh`). Set to 1 per core available. 

- **Security & identity**
  - **`SECRET_KEY`**: application secret key for signing sessions and API tokens.  
    - **Required in production**.  
    - The example compose sets `SECRET_KEY="change-me-in-production"` – you **must change this**.
    - It should be 32 hexadecimal characters, you can generate one using the following commands `openssl rand -hex 32`. 
    - This secret is used to generate and verify API keys, if you change it all previously generated API keys will become invalid. 
  - **`DEFAULT_PASSWORD_COMMUNICATION`**: preferred channel for password communication (`email` or `sms`).

- **External URLs & integrations**
  - **`SUPPORT_EMAIL`**, **`SUPPORT_URL`**: contact points displayed in the UI and emails. They should be provided so that your users know who to contact and where to look for information. 
  - **`GOOGLE_MAPS_API_KEY`**, **`GOOGLE_CAPTCHA_SITE_KEY`** (required): Google Maps and reCAPTCHA integration keys. Those are required for the platform to function properly. 
  - **`ANTHROPIC_API_KEY`** (optional): key for AI‑powered features using Claude AI models. If not provided all AI features will be disabled. 
  - **`LOGIN_OAUTH_URL`**, **`LOGIN_JWT_SECRET`** (optional): configuration for an external login platform / SSO.

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
  - Managed **PostgreSQL** (or high‑availability cluster), for PaygOps (and for Analytical DB and OpenPAYGO if you use it as well). 
  - Managed **Redis**.
  - A reverse proxy (e.g. **nginx**, Traefik) terminating TLS and routing to:
    - `web` service on port `8000`.
    - `api` service on port `6789` mapping to `/api/v1/`.
    - (Optionally, for device upload) `openpaygo` service on port 5001 mapping to `/openpaygo`

- **Configure backups and monitoring** for PostgreSQL and Redis and set:
  - `PAYG_URL` to the public HTTPS URL of your instance.
  - Strong values for `SECRET_KEY`, database credentials, and any third‑party API keys.

### User documentation (Doc360)

End‑user and functional documentation for PaygOps is maintained in the **PaygOps Doc360** portal. Access to Doc360 is provided to customers and partners; contact your PaygOps representative or administrator to obtain access. 

---

## Codebase Structure

### Key frameworks and libraries

- **Backend framework**: `Flask` (with  `Flask-RESTful`).
- **Background jobs**: `Celery` with `redis` and `celery-redbeat`.
- **Data layer**: `PostgreSQL` with `psycopg2-binary` and `pony` ORM.
- **Web server**: `gunicorn` behind a proxy.
- **Testing & quality**: `pytest`, `factory-boy`, `Faker`, `coverage`.
- **Other utilities**: `requests`, `pyjwt`, `jsonschema`, `python-dateutil`, `Pillow`, and optional AI & third‑party integrations.

### Folder structure (high level)

From the root:

- **`api_app/`**: main public API application (Flask app for programmatic access).
- **`web_app/`**: main web application (Flask app, HTML templates, JS assets).
- **`data_system/`**: analytical DB access, statistics, exports and data services.
- **`shared/`**: shared helpers, services, logging, migrations, and common utilities.
- **`core_system/`**: core entities such as clients, users, roles, phone numbers, portfolios.
- **`accounting_system/`**: accounting domain (accounts, expenses, reports).
- **`admin/`**: admin APIs, API keys, password management, and admin web UI.
- **`messages_system/`**: messaging models, services, and web/API views (e.g. SMS).
- **`payg_loan_system/`**: PAYGO loan logic, contracts, devices, offers, payments.
- **`sales_system/`**: sales, leads, orders and related flows.
- **`stock_management_system/`**: stock and inventory management.
- **`survey_system/`**: custom forms models, flows and UI.
- **`worker_app/` / `worker_green_app/`**: Celery worker entry points and configuration.
- **`shared/`**: shared helpers, services, logging, migrations, and common utilities.
- **`tests/`**: automated tests for the modules.
- **`config.py` / `constants.py`**: global configuration and constants.
- **`Dockerfile`**: build instructions for the Docker image.
- **`entrypoint.sh`**: multi‑command entrypoint (web, API, workers, tests, migrations).
- **`requirements.txt`**: Python dependencies.
- **`docker-compose.yml`**: basic local development stack (this file).

### Running tests

You can run tests either inside Docker (recommended for consistency) or directly on your machine.

- **Using Docker Compose**

```bash
# Run the full test suite
docker compose run --rm web test

# Run tests with coverage
docker compose run --rm web test coverage
```

The `web` service uses the same image and entrypoint; the `test` command is routed to the `test` branch in `entrypoint.sh`.

---

## Contributing

Please read our [Contributing Guidelines](CONTRIBUTING.md) for details on how to contribute to this project.

---

## License

This project is licensed under the terms described in our [License](LICENSE.md).  
Please read that file carefully before deploying PaygOps Community in production or redistributing modified versions.


