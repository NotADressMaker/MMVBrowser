const exampleOptions = [
  { label: "List worthy records", path: "/examples/scripts/list-worthy-records.gai" },
  { label: "Inspect task", path: "/examples/scripts/inspect-task.gai" },
  { label: "Verify on-chain", path: "/examples/scripts/verify-onchain.gai" },
  { label: "Summarize evidence", path: "/examples/scripts/summarize-evidence.gai" },
];

const elements = {
  exampleSelect: document.getElementById("exampleSelect"),
  loadExample: document.getElementById("loadExample"),
  scriptInput: document.getElementById("scriptInput"),
  varsInput: document.getElementById("varsInput"),
  runScript: document.getElementById("runScript"),
  allowLlm: document.getElementById("allowLlm"),
  stdout: document.getElementById("stdout"),
  artifacts: document.getElementById("artifacts"),
  errors: document.getElementById("errors"),
  apiBaseUrl: document.getElementById("apiBaseUrl"),
  ipfsGateway: document.getElementById("ipfsGateway"),
  rpcUrl: document.getElementById("rpcUrl"),
};

function setOutput({ stdout = "", artifacts = {}, errors = [] }) {
  elements.stdout.textContent = stdout || "(no output)";
  elements.artifacts.textContent = JSON.stringify(artifacts || {}, null, 2);
  elements.errors.textContent = errors.length ? errors.join("\n") : "(no errors)";
}

function populateExamples() {
  exampleOptions.forEach((example) => {
    const option = document.createElement("option");
    option.value = example.path;
    option.textContent = example.label;
    elements.exampleSelect.appendChild(option);
  });
}

async function loadExample() {
  const path = elements.exampleSelect.value;
  const response = await fetch(path);
  const text = await response.text();
  elements.scriptInput.value = text.trim();
}

async function loadConfig() {
  const response = await fetch("/api/scripts/config");
  const config = await response.json();
  elements.apiBaseUrl.value = config.apiBaseUrl || "";
  elements.ipfsGateway.value = config.ipfsGateway || "";
  elements.rpcUrl.value = config.rpcUrl || "";
  if (!config.allowLlm) {
    elements.allowLlm.checked = false;
    elements.allowLlm.disabled = true;
    elements.allowLlm.parentElement.classList.add("disabled");
  }
}

async function runScript() {
  setOutput({ stdout: "Running...", artifacts: {}, errors: [] });
  let vars = {};
  if (elements.varsInput.value.trim()) {
    try {
      vars = JSON.parse(elements.varsInput.value);
    } catch (error) {
      setOutput({ stdout: "", artifacts: {}, errors: ["Variables JSON is invalid."] });
      return;
    }
  }

  const response = await fetch("/api/scripts/run", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      script: elements.scriptInput.value,
      vars,
      allow_llm: elements.allowLlm.checked,
    }),
  });
  const data = await response.json();
  setOutput(data);
}

populateExamples();
loadConfig();
loadExample();

if (elements.loadExample) {
  elements.loadExample.addEventListener("click", () => loadExample());
}
if (elements.runScript) {
  elements.runScript.addEventListener("click", () => runScript());
}
