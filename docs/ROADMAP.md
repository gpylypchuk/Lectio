# Lectio Roadmap

## Current status
| Field | Value |
|---|---|
| Current phase | 6 Public deployment |
| Last step done | /healthz renamed to /health |
| Next step | Serve the frontend from the API container |
| Blockers | None |

## Phase 0. Setup (done)
* [x] Folder structure and Python tooling
* [x] CLAUDE.md, docs and Claude Code commands
* [x] First commit
Done when ruff, mypy and pytest run cleanly on the empty project.

## Phase 1. Local backend (done)
* [x] app/config.py with pydantic settings
* [x] app/schemas.py with AnalysisRequest, PaperSummary (with a business rule in a model_validator) and AnalysisResult
* [x] app/llm.py with forced tool use, Pydantic validation and one retry that feeds the error back to the model
* [x] app/main.py with lifespan, /healthz and POST /v1/analyses returning 422, 502 and 503 as appropriate
* [x] Endpoint tests with a fake LLM via dependency_overrides, and tests for the retry logic
* [x] Dockerfile and a local run with docker run. The local docker run was skipped; the image is first built and run in Phase 2
Done when a local curl returns a real summary, the tests pass and the image runs.

## Phase 2. GCP by hand
* [x] Project, billing and budget alert
* [x] Enable the Cloud Run, Artifact Registry, Cloud Build, Secret Manager and Cloud Deploy APIs. Cloud Deploy deferred to Phase 3
* [x] Artifact Registry repository and image build with Cloud Build
* [x] Secret with the API key in Secret Manager
* [x] Dedicated service account for the service, allowed only to read that secret
* [x] Cloud Run deploy with the secret exposed as an environment variable
* [x] New revision, traffic split between revisions and rollback
* [x] Read the logs in Cloud Logging
* [x] Rename /healthz to /health. On Cloud Run, /healthz got Google's own 404 and never reached the container
Done when the public URL responds and every command and flag used can be explained.

## Phase 3. Cloud Deploy
* [x] deploy/skaffold.yaml and deploy/service.yaml
* [x] deploy/clouddeploy.yaml with a dev and prod pipeline, prod requiring approval
* [x] Create a release, watch the rollout in dev, promote to prod and approve
* [ ] Rollback. Deferred, it needs a second release on prod
Done when a new version reaches prod only through promotion and approval.

## Phase 4. CI (done)
* [x] .github/workflows/ci.yml running ruff, mypy and pytest on every push and PR
* [ ] Optional. Automatic build and release authenticating with Workload Identity Federation
Done when CI is green.

## Phase 5. Optional
Only once everything above is done. A minimal React frontend, or async processing with Pub/Sub.
* [x] Local React frontend in frontend/. Vite proxies /v1 to port 8080, and PDF text is extracted in the browser with pdf.js

## Phase 6. Public deployment
Keep the app running publicly at near zero idle cost, with the LLM spend capped.
* [x] Rename /healthz to /health
* [ ] Serve the built frontend from the API container with a multi-stage Dockerfile
* [ ] Per IP rate limiting in the app and a lower containerConcurrency
* [ ] Monthly spend limit in the Anthropic Console
* [ ] Public lectio-prod with allUsers as run.invoker, recorded as a decision that supersedes D16
* [ ] Delete lectio-api and add an Artifact Registry cleanup policy
* [ ] Optional. Release on push with Workload Identity Federation, and a Cloud Deploy rollback
Done when the public URL serves the frontend and a burst of requests gets 429.

## Out of scope
Cloud SQL, Pub/Sub with a worker and Terraform. See `docs/ARCHITECTURE.md` for how they would fit.
