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
