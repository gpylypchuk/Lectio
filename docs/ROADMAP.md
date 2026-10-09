# Lectio Roadmap

## Current status
| Field | Value |
|---|---|
| Current phase | 2 GCP by hand (done except the /healthz rename) |
| Last step done | Revision 00002 tagged candidate, 50/50 split and rollback to 00001 |
| Next step | Rename /healthz to /health, then Phase 3 Cloud Deploy |
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
* [ ] Rename /healthz to /health. On Cloud Run, /healthz got Google's own 404 and never reached the container
Done when the public URL responds and every command and flag used can be explained.

## Phase 3. Cloud Deploy
* [ ] deploy/skaffold.yaml and deploy/service.yaml
* [ ] deploy/clouddeploy.yaml with a dev and prod pipeline, prod requiring approval
* [ ] Create a release, watch the rollout in dev, promote to prod and approve
* [ ] Rollback
Done when a new version reaches prod only through promotion and approval.

## Phase 4. CI
* [ ] .github/workflows/ci.yml running ruff, mypy and pytest on every push and PR
* [ ] Optional. Automatic build and release authenticating with Workload Identity Federation
Done when CI is green.

## Phase 5. Optional
Only once everything above is done. A minimal React frontend, or async processing with Pub/Sub.

## Out of scope
Cloud SQL, Pub/Sub with a worker and Terraform. See `docs/ARCHITECTURE.md` for how they would fit.
