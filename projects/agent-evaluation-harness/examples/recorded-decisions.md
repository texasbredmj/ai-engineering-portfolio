# Recorded model decision contract

Supply JSONL with one decision for every case in the selected suite, with exactly matching case IDs:

```json
{"case_id":"sum-positive","call":{"tool":"math.sum","arguments":{"a":7,"b":5}},"retry_limit":3,"input_tokens":120,"output_tokens":30,"model_latency_ms":450.0,"claims_verified":true}
```

This single example is not a complete predictions file. Use the benchmark file to see all case IDs
and task inputs. `claims_verified` claims that acceptance criteria will be met, including safe rejection
or an expected failure; its accuracy is judged independently. Input/output token counts and model
latency must be explicitly present, even if they are zero. Retry limit is 1–3. Arbitrary tool names
can be recorded to measure wrong selection, but they are never executed; the backend rejects them.

Keep provider invocation in a separate authorized recording process. Do not include API keys,
raw prompts, or private outputs in this contract. The current adapter boundary evaluates recorded
structured decisions through mock tools. It does not invoke an external model or replay its network tools.
