const config = {
  apiBaseUrl: process.env.API_BASE_URL || "http://localhost:8080",
  ipfsGateway: process.env.IPFS_GATEWAY || "https://ipfs.io",
  rpcUrl: process.env.RPC_URL || "",
  allowLlm: (process.env.ALLOW_LLM_SUMMARIZATION || "false").toLowerCase() === "true",
  runnerPython: process.env.GENAIL_RUNNER_PYTHON || "python3",
  timeoutMs: Number(process.env.GENAIL_TIMEOUT_MS || "10000"),
  scriptLimitBytes: Number(process.env.GENAIL_SCRIPT_LIMIT_BYTES || "51200"),
};

module.exports = { config };
