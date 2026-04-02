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
