# mmv-browser

A standalone, read-only browser for MMV that includes a GenAIL script runner for querying and summarizing MMV records, receipts, and evidence bundles.

## Running locally

```bash
npm install
npm run dev
```

The server will start on `http://localhost:3000` and expose a scripts page at `/scripts`.

### Environment variables

| Variable | Description | Default |
| --- | --- | --- |
| `API_BASE_URL` | MMV API base URL | `http://localhost:8080` |
| `IPFS_GATEWAY` | IPFS HTTP gateway base | `https://ipfs.io` |
| `RPC_URL` | Optional RPC endpoint for verification | empty |
| `GENAIL_RUNNER_PYTHON` | Python executable for GenAIL runner | `python3` |
| `GENAIL_TIMEOUT_MS` | Script timeout in milliseconds | `10000` |
| `GENAIL_SCRIPT_LIMIT_BYTES` | Max script size | `51200` |
| `ALLOW_LLM_SUMMARIZATION` | Enables `generate` statements server-side | `false` |

LLM summarization uses server-side environment keys only (for example `OPENAI_API_KEY`). The browser UI never prompts for API keys.

## GenAIL scripts

Visit `/scripts` to load and run example `.gai` scripts. Example scripts live in `examples/scripts`.

## Security model

The script runner is intentionally constrained:

- Tooling is allowlisted to MMV read-only APIs + optional RPC verification.
- Script size, tool call count, and output size are limited.
- Requests are restricted to configured MMV/IPFS/RPC hosts; private network addresses are blocked by default.
- LLM `generate` is disabled unless `ALLOW_LLM_SUMMARIZATION=true` is set on the server.

See [docs/GENAIL_INTEGRATION.md](docs/GENAIL_INTEGRATION.md) for supported statements, tools, and troubleshooting.
