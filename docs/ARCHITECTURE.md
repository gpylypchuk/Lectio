# Architecture

## Current
Browser → Cloud Run (FastAPI serving the React build and `/v1`) → Anthropic API

* Secret Manager holds the API key, injected as an environment variable.
* Cloud Build builds the image and pushes it to Artifact Registry.
* Cloud Deploy promotes releases from lectio-dev (private) to lectio-prod (public, approval required).
* GitHub Actions runs ruff, mypy and pytest on every push.

### Request flow
1. `POST /v1/analyses` with the paper text. Pydantic validates it, or 422.
2. The rate limiter checks the per IP and total quotas, or 429.
3. The LLM is called with a forced tool generated from PaperSummary.
4. The output is validated, with one retry on failure, or 502.
5. Provider failures after SDK retries return 503. Success returns 200 with the summary.

## Scaling path
* Async processing: POST returns 202, Pub/Sub, a worker service, idempotency by id and a dead letter topic.
* Shared rate limiting with Memorystore or Cloud Armor once there is more than one instance.
* Frontend on a CDN, deployed independently.
* Persistence with Cloud SQL, SQLAlchemy and Alembic.
* Infrastructure as code with Terraform and remote state in Cloud Storage.
* An eval set in CI for prompt and model changes.
* A cache keyed by text hash.
