# Roadmap

## Current status
| Field | Value |
|---|---|
| Current phase | 6 Public deployment |
| Last step done | lectio-prod public |
| Next step | Delete lectio-api and apply the Artifact Registry cleanup policy |
| Blockers | None |

## Completed
1. Local backend: FastAPI, Pydantic schemas, LLM client with forced tool use and a validation retry, tests with a fake LLM.
2. GCP: Artifact Registry, Cloud Build, Secret Manager, a dedicated service account and Cloud Run.
3. Cloud Deploy pipeline from dev to prod with approval.
4. CI on GitHub Actions with ruff, mypy and pytest.
5. React frontend with text and PDF input.

## Phase 6. Public deployment
* [x] Serve the frontend from the API container
* [x] Rate limiting per IP and in total
* [x] Spend limit of 5 USD per month in the Anthropic Console
* [x] Public lectio-prod
* [ ] Delete lectio-api and apply the Artifact Registry cleanup policy

## Backlog
* Release on push to main with Workload Identity Federation.
* Cloud Deploy rollback drill.
* Build the frontend in CI.

## Out of scope
Cloud SQL, a Pub/Sub worker and Terraform. See `ARCHITECTURE.md`.
