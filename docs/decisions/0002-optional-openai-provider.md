# ADR 0002: Deterministic Default, Optional OpenAI Provider

Status: accepted for V1.

CI and normal local evaluation use a deterministic stub. An optional OpenAI
Responses API adapter is configured only with an explicit provider, model, and
credential. It uses strict structured output, no tools, redacted context, and
`store=false`. Provider errors or invalid output cannot bypass deterministic
controls and result in a safe fallback or escalation.
