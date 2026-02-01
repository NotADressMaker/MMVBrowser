# GenAIL integration

The mmv-browser script runner supports a minimal subset of GenAIL's DSL for read-only MMV exploration.

## Supported statements

- `set name = value` (JSON literals, numbers, strings, booleans)
- `template name = "..."`
- `prompt name = "..."`
- `message role = "..."`
- `call tool_name into var with { ... }`
- `print var_or_string`
- `generate var` (disabled unless `ALLOW_LLM_SUMMARIZATION=true`)

## Allowlisted tools

- `mmv_list_records(min_score_bps=8000, limit=50, offset=0, program_id=null)`
- `mmv_get_record(task_id)`
- `mmv_get_receipt(task_id)`
- `mmv_get_audit(task_id)`
- `mmv_fetch_evidence(bundle_uri)` (supports `ipfs://` and `https://`)
- `mmv_verify_onchain(task_id, bundle_hash, chain_id, contract_address, rpc_url)` (optional)

Tool responses are JSON-serializable and are included in the script output `artifacts` object.

## Example scripts

The repository includes example `.gai` scripts under `examples/scripts`:

- `list-worthy-records.gai`
- `inspect-task.gai`
- `verify-onchain.gai`
- `summarize-evidence.gai`

Load them from the `/scripts` UI or open them directly under `/examples/scripts`.

## LLM summarization

`generate` statements are disabled by default. To enable server-side summarization:

1. Set `ALLOW_LLM_SUMMARIZATION=true`.
2. Provide provider keys through environment variables (e.g. `OPENAI_API_KEY`).

The browser UI never asks for API keys. If `generate` is used while disabled, the runner returns a clear error: `generate disabled; enable ALLOW_LLM_SUMMARIZATION`.

## Security limits

- Script size limit defaults to 50KB (`GENAIL_SCRIPT_LIMIT_BYTES`).
- Tool call limit defaults to 20 calls per run (`GENAIL_TOOL_CALL_LIMIT`).
- Script timeout defaults to 10s (`GENAIL_TIMEOUT_MS`).
- Network requests are restricted to configured MMV/IPFS/RPC hosts; private network addresses are blocked unless `GENAIL_ALLOW_PRIVATE_NETWORK=true`.

## Troubleshooting

- **No output**: Check the server logs for `genail_run` entries and ensure MMV endpoints are reachable.
- **generate disabled**: Enable `ALLOW_LLM_SUMMARIZATION` and set a provider key on the server.
- **tool not allowed**: Ensure the script only uses the allowlisted tool names above.
