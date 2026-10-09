# Decisions

## D1. FastAPI instead of Django
Why. It is a pure API with heavy I/O towards the LLM. FastAPI provides native async, Pydantic validation and automatic docs.
Trade off. What Django ships with (ORM, admin, auth) has to be added separately if needed.

## D2. Forced tool use and Pydantic validation
Why. It guarantees JSON output with a known shape, and a single model defines both the schema and the validation. The LLM proposes, the code validates.
Trade off. A retry adds latency and tokens.

## D3. Synchronous analysis in this version
Why. A summary takes a few seconds and this keeps everything simple.
Trade off. Long texts or traffic spikes would require moving to Pub/Sub with a worker.

## D4. Cloud Run instead of GKE
Why. A stateless service with no need to operate a cluster. It scales automatically, even to zero.
Trade off. Less fine-grained control and stateless services only.

## D5. us-central1 region
Why. All the services are available and prices are low. Latency is not critical.
Trade off. Higher latency for users in South America than a region there.

## D6. Configuration with pydantic settings
Why. Config comes from environment variables and is validated at startup, so a missing API key fails fast instead of on the first request. The key is a SecretStr so it never leaks into logs. LLM_MODEL defaults to the pinned snapshot claude-haiku-4-5-20251001 because it is not a secret and a safe default avoids setting it in every environment.
Trade off. A pinned snapshot does not pick up newer models on its own. Changing it is a config change, not a code change.

## D7. Forced tool use depends on the model
Why. D2 relies on forced tool_choice. Per Anthropic's model docs, Claude Fable 5.1, Opus 5.5 and Sonnet 5.5 reject tool_choice "tool" and "any" with a 400. Haiku 4.5, the default, accepts it (so does Haiku 5.5), so the design stays.
Alternative. On those models, use tool_choice "auto" with the tool named in the prompt and strict: true on the tool, then check that the call was made and retry if not. Or use structured outputs (output_config.format), since the forced call only exists to get JSON back. Pydantic validation and the retry stay the same.
Trade off. For those models, changing LLM_MODEL is not only a config change as D6 suggests. llm.py has to change too.

## D8. Provider error mapping
Why. The rule is that whatever the SDK retries is transient: timeouts, connection errors, 408, 409, 429 and 5xx (529 included). If they still fail after the SDK retries, they map to 503 and the client can retry later. Any other 4xx (bad request, invalid key, unknown model) is a bug or misconfiguration on our side that a retry will not fix, so it maps to 500 and is logged with the status code, error type, provider request id and model. Classification goes by status code, not exception class, because in the SDK 529 is OverloadedError, which does not inherit from InternalServerError. The 503 carries Retry-After: 30, long enough for a rate limit or an overload to clear. An invalid LLM answer still maps to 502.
Trade off. The client only sees a generic 500. The detail lives in the logs.

## D9. Text length limits
Why. AnalysisRequest.text accepts 500 to 100,000 characters after trimming surrounding whitespace. The maximum is roughly 25,000 tokens, which caps cost (about $0.025 of input per call with Haiku 4.5) and the latency of a synchronous request (D3), well within the model context. The minimum rejects inputs that cannot be a paper before paying for a call.
Trade off. Longer papers get a 422. Supporting them would need chunking or the async path.

## D10. Every rule on LLM output must be satisfiable without inventing data
Why. A rule that can only pass by adding content pushes the model to make it up, and the retry reinforces it. Every rule needs an honest way out. That is why title is nullable, limitations can be empty, and the only cross-field rule caps confidence: it cannot be high without a title and at least two key findings, and the honest fix is to lower it. The rule is also stated in the field description so the model usually gets it right on the first attempt. Rejected: "empirical requires at least one limitation", which invites invented limitations.
Trade off. Clients must handle a null title and more low or medium confidence answers.

## D11. Prompt injection defense
Why. The paper is untrusted input. It goes between <paper> tags, any closing tag inside it is neutralized so it cannot end the block early, and the system prompt says that content inside the tags is data to analyze, never instructions. Forced tool use and Pydantic validation limit the blast radius: the model has no tools with side effects and the only possible output is a PaperSummary.
Trade off. It is a mitigation, not a guarantee. A crafted paper can still bias the content of its own summary.

## D12. Two retry layers and an overall deadline
Why. The SDK retries transport failures (D8) with exponential backoff, and our code retries content failures once (D2). They handle different failures and never overlap: we do not retry provider errors, because the SDK already did. They do multiply: each validation attempt can make 1 + LLM_MAX_RETRIES HTTP requests of up to LLM_TIMEOUT_SECONDS (30 s) each, and the SDK honors retry-after with no practical cap. LLM_DEADLINE_SECONDS (90 s) bounds the whole analysis and maps to 503. It stays below the Cloud Run request timeout (300 s by default) so the client gets a clean 503 instead of a cut connection. max_retries is set explicitly when the client is created so the budget is visible in code.
Trade off. A slow but healthy provider can hit the deadline and return 503 for a request that would have succeeded.

## D13. /health does not depend on the LLM provider
Why. It is a liveness check: it only says the process is up and serving. If it called Anthropic, a provider outage would make Cloud Run treat healthy instances as broken and restart them, which fixes nothing and adds cold starts. The path is /health and not /healthz because Cloud Run answered /healthz with its own 404 before the request reached the container.
Trade off. A healthy /health does not mean analyses work. Provider health shows up in the 503 rate instead.

## D14. Container image
Why. python:3.12-slim keeps the image small without the build issues of Alpine. Dependencies are installed before the code is copied, so code changes reuse the cached layer. The process runs as a non-root user. uvicorn listens on 0.0.0.0 and on the PORT that Cloud Run sets, and runs through exec so it receives SIGTERM and the lifespan can close the client. .dockerignore keeps .env out of the build context, and the API key is injected at run time (docker run --env-file locally, Secret Manager on Cloud Run).
Trade off. The base image tag floats on patch releases. Pinning a digest would make builds fully reproducible at the cost of manual updates.

## D15. Images are built with Cloud Build
Why. The development machine is ARM and Cloud Run runs amd64, so a local build would need cross compilation. Cloud Build builds on amd64, the result does not depend on a laptop, and the image goes straight to Artifact Registry in us-central1. .gcloudignore mirrors .dockerignore because the source is uploaded to a Cloud Storage bucket before Docker runs.
Trade off. Each build uploads the source and waits for a remote worker, which is slower than a cached local build.

## D16. Private service with least privilege and a cost cap
Why. Every request spends API credits, so the service is deployed with --no-allow-unauthenticated and only identities with run.invoker can call it. It runs as a dedicated service account whose only permission is secretAccessor on the one secret, bound on the secret and not on the project. The secret is pinned to a version, so rotating the key is an explicit deploy that creates a new revision. --max-instances 1 caps the cost.
Trade off. Callers need an identity token, so a public frontend would need an authenticated layer in front. One instance limits throughput to what a single container can serve.

## D17. Cloud Deploy pipeline from dev to prod
Why. A release is immutable: the image is pinned by digest and the manifests are rendered once, so prod runs exactly what ran in dev. One Knative manifest serves both targets, with the service name set per target through a deploy parameter. Prod requires approval, which separates the permission to deploy from the permission to approve. The Phase 2 service lectio-api stays outside the pipeline as a fallback.
Trade off. Dev and prod share one project, and Cloud Deploy runs as the Compute Engine default service account, which has Editor. A real setup would use one project per environment and a dedicated execution service account for the pipeline.

## D18. The API container also serves the frontend
Why. A multi-stage Dockerfile builds the React app with Node and copies only the static output into the Python image, so Node never reaches production. FastAPI mounts it at / after every API route, so /v1 and /health still win. The browser calls /v1 on the same origin, which needs no CORS, and one Cloud Run service with one URL keeps idle cost at zero. The build context moves to the repo root because the image now needs backend and frontend, and .dockerignore and .gcloudignore move with it. Locally the directory is absent and Vite keeps serving the frontend with its proxy.
Trade off. Frontend and API are released together, and static files are served by uvicorn instead of a CDN. A separate frontend on Firebase Hosting or Cloud Storage with a CDN would scale better and deploy independently.

## D19. In-memory rate limiting for the public service
Why. Once the service is public, every accepted analysis spends API credits. POST /v1/analyses allows 5 analyses per IP and 30 in total per sliding hour, and answers 429 with Retry-After beyond that. The cap per IP keeps one person from using everyone's quota, and the total cap holds when someone rotates IPs. The check runs after body validation, so a rejected body costs nothing and uses no quota. State lives in memory, which is correct because maxScale is 1: the only instance sees every request. The window keeps one entry per accepted request, so memory is bounded by the total cap and not by distinct clients. The client IP is the last X-Forwarded-For entry, because Google's front end appends the address it saw and anything to its left can be forged. No Cloud Run page states this, so it is checked after deploy with a forged header, and the IP is logged on every 429. The hard cap on spend is the monthly limit in the Anthropic Console, not this code.
Trade off. The counters reset when the instance restarts, and more than one instance would multiply the caps. Several instances would need shared state such as Memorystore, or Cloud Armor in front of a load balancer. People behind one NAT share the cap per IP.
