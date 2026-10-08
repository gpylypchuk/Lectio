# Lectio Roadmap

## Current status
| Field | Value |
|---|---|
| Current phase | 0 Setup |
| Last step done | Folder structure, Python tooling and context files |
| Next step | First commit |
| Blockers | None |

## Phase 0. Setup
* [x] Folder structure and Python tooling
* [x] CLAUDE.md, docs and Claude Code commands
* [ ] First commit
Done when ruff, mypy and pytest run cleanly on the empty project.

## Phase 1. Local backend
* [ ] app/config.py with pydantic settings
* [ ] app/schemas.py with AnalysisRequest, PaperSummary (with a business rule in a model_validator) and AnalysisResult
* [ ] app/llm.py with forced tool use, Pydantic validation and one retry that feeds the error back to the model
* [ ] app/main.py with lifespan, /healthz and POST /v1/analyses returning 422, 502 and 503 as appropriate
* [ ] Endpoint tests with a fake LLM via dependency_overrides, and tests for the retry logic
* [ ] Dockerfile and a local run with docker run
Done when a local curl returns a real summary, the tests pass and the image runs.

## Phase 2. GCP by hand
* [ ] Project, billing and budget alert
* [ ] Enable the Cloud Run, Artifact Registry, Cloud Build, Secret Manager and Cloud Deploy APIs
* [ ] Artifact Registry repository and image build with Cloud Build
* [ ] Secret with the API key in Secret Manager
* [ ] Dedicated service account for the service, allowed only to read that secret
* [ ] Cloud Run deploy with the secret exposed as an environment variable
* [ ] New revision, traffic split between revisions and rollback
* [ ] Read the logs in Cloud Logging
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
