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
