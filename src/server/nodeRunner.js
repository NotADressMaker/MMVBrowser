const { listRecords } = require("./mmvClient");

function parseCallArgs(script) {
  const callLine = script.split("\n").find((line) => line.trim().startsWith("call "));
  if (!callLine) {
    return {};
  }
  const match = callLine.match(/call\s+mmv_list_records\s+into\s+\w+(?:\s+with\s+(.+))?/);
  if (!match) {
    return {};
  }
  const blob = match[1];
  if (blob && blob.trim().startsWith("{")) {
    return JSON.parse(blob);
  }
  return {};
}

async function runNodeRunner({ script, toolConfig }) {
  const args = parseCallArgs(script);
  const records = await listRecords({
    apiBaseUrl: toolConfig.api_base_url,
    minScoreBps: args.min_score_bps ?? 8000,
    limit: args.limit ?? 50,
    offset: args.offset ?? 0,
    programId: args.program_id ?? null,
  });
  return {
    stdout: JSON.stringify(records, null, 2) + "\n",
    artifacts: { records },
    errors: [],
  };
}

module.exports = { runNodeRunner };
