const { ipfsToGateway } = require("./ipfs");

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`MMV request failed: ${response.status}`);
  }
  return response.json();
}

function buildApiUrl(apiBaseUrl, path) {
  return `${apiBaseUrl.replace(/\/$/, "")}${path}`;
}

async function listRecords({ apiBaseUrl, minScoreBps = 8000, limit = 50, offset = 0, programId = null }) {
  const url = new URL(buildApiUrl(apiBaseUrl, "/records"));
  url.searchParams.set("min_score_bps", String(minScoreBps));
  url.searchParams.set("limit", String(limit));
  url.searchParams.set("offset", String(offset));
  if (programId) {
    url.searchParams.set("program_id", programId);
  }
  return requestJson(url.toString());
}

async function getRecord({ apiBaseUrl, taskId }) {
  return requestJson(buildApiUrl(apiBaseUrl, `/records/${taskId}`));
}

async function getReceipt({ apiBaseUrl, taskId }) {
  return requestJson(buildApiUrl(apiBaseUrl, `/receipts/${taskId}`));
}

async function getAudit({ apiBaseUrl, taskId }) {
  return requestJson(buildApiUrl(apiBaseUrl, `/audits/${taskId}`));
}

async function fetchEvidence({ ipfsGateway, bundleUri }) {
  const resolved = ipfsToGateway(ipfsGateway, bundleUri);
  return requestJson(resolved);
}

async function verifyOnchain({ rpcUrl, contractAddress }) {
  const payload = {
    jsonrpc: "2.0",
    method: "eth_call",
    params: [
      {
        to: contractAddress,
        data: "0x",
      },
      "latest",
    ],
    id: 1,
  };
  return requestJson(rpcUrl, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
}

module.exports = {
  buildApiUrl,
  listRecords,
  getRecord,
  getReceipt,
  getAudit,
  fetchEvidence,
  verifyOnchain,
};
