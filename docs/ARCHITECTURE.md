# Architecture

## Today
Client → Cloud Run (FastAPI) → Anthropic API.
The API key lives in Secret Manager and Cloud Run injects it as an environment variable. Images are stored in Artifact Registry. Cloud Deploy promotes versions from dev to prod with an approval.

Request flow
1. The client sends the text to POST /v1/analyses.
2. Pydantic validates the body. If it is invalid, 422.
3. The LLM is called with a forced tool whose schema is generated from PaperSummary.
4. Pydantic validates the LLM output, including the business rule. If it fails, one retry with the error as context.
5. If it fails again, 502. If the provider does not respond, 503. If everything is fine, 200 with the summary.

## How it would scale
* Async processing. POST returns 202 with an id, a message is published to Pub/Sub and a worker in a separate Cloud Run service processes it. Idempotency by id and a dead letter topic.
* Persistence. Cloud SQL (Postgres) with SQLAlchemy and Alembic to store analyses and history.
* Infrastructure as code. Everything from phase 2 in Terraform, with the state in a Cloud Storage bucket.
* LLM quality. An eval set that runs in CI on every prompt or model change.
* Cost and latency. Cache by text hash and a small model by default.
