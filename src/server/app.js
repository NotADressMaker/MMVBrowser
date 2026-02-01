const express = require("express");
const path = require("path");
const { spawn } = require("child_process");
const { randomUUID } = require("crypto");
const { config } = require("./config");
const { runNodeRunner } = require("./nodeRunner");

const app = express();
app.use(express.json({ limit: "100kb" }));

app.use("/", express.static(path.join(__dirname, "..", "..", "public")));
app.use("/examples", express.static(path.join(__dirname, "..", "..", "examples")));

app.get("/scripts", (req, res) => {
  res.sendFile(path.join(__dirname, "..", "..", "public", "scripts.html"));
});

app.get("/api/scripts/config", (req, res) => {
  res.json({
    apiBaseUrl: config.apiBaseUrl,
    ipfsGateway: config.ipfsGateway,
    rpcUrl: config.rpcUrl,
    allowLlm: config.allowLlm,
  });
});

app.post("/api/scripts/run", async (req, res) => {
  const requestId = randomUUID();
  const start = Date.now();
  try {
    const { script, vars = {}, mode = "run", allow_llm = false } = req.body || {};
    if (typeof script !== "string") {
      return res.status(400).json({ stdout: "", artifacts: {}, errors: ["script must be a string"] });
    }
    if (Buffer.byteLength(script, "utf8") > config.scriptLimitBytes) {
      return res.status(400).json({ stdout: "", artifacts: {}, errors: ["script too large"] });
    }
    const payload = {
      script,
      vars,
      mode,
      allow_llm: config.allowLlm && allow_llm,
      timeout_s: Math.ceil(config.timeoutMs / 1000),
      tool_config: {
        api_base_url: config.apiBaseUrl,
        ipfs_gateway: config.ipfsGateway,
        rpc_url: config.rpcUrl || null,
      },
    };

    if (process.env.GENAIL_RUNNER_MODE === "node") {
      const result = await runNodeRunner({ script, toolConfig: payload.tool_config });
      return res.json(result);
    }

    const runnerPath = path.join(__dirname, "..", "..", "genail_runner", "runner.py");
    const child = spawn(config.runnerPython, [runnerPath], {
      stdio: ["pipe", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    const timeoutId = setTimeout(() => {
      child.kill("SIGKILL");
    }, config.timeoutMs);

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString("utf8");
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString("utf8");
    });

    child.on("close", (code) => {
      clearTimeout(timeoutId);
      const duration = Date.now() - start;
      console.info("genail_run", { requestId, duration, exitCode: code });
      if (stderr) {
        console.warn("genail_run_stderr", { requestId, stderr: stderr.slice(0, 200) });
      }
      try {
        const parsed = stdout ? JSON.parse(stdout) : { stdout: "", artifacts: {}, errors: ["empty response"] };
        return res.json(parsed);
      } catch (error) {
        return res.status(500).json({ stdout: "", artifacts: {}, errors: ["runner output invalid"] });
      }
    });

    child.stdin.write(JSON.stringify(payload));
    child.stdin.end();
  } catch (error) {
    console.error("genail_run_error", { requestId, error: error.message });
    res.status(500).json({ stdout: "", artifacts: {}, errors: ["runner failed"] });
  }
});

module.exports = { app };
