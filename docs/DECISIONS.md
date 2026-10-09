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

## D13. /healthz does not depend on the LLM provider
Why. It is a liveness check: it only says the process is up and serving. If it called Anthropic, a provider outage would make Cloud Run treat healthy instances as broken and restart them, which fixes nothing and adds cold starts.
Trade off. A healthy /healthz does not mean analyses work. Provider health shows up in the 503 rate instead.
