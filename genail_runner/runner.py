import json
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

import requests

SCRIPT_LIMIT_BYTES = int(os.getenv("GENAIL_SCRIPT_LIMIT_BYTES", "51200"))
TOOL_CALL_LIMIT = int(os.getenv("GENAIL_TOOL_CALL_LIMIT", "20"))
MAX_OUTPUT_BYTES = int(os.getenv("GENAIL_MAX_OUTPUT_BYTES", "65536"))
DEFAULT_TIMEOUT_S = int(os.getenv("GENAIL_TIMEOUT_S", "10"))
DEV_ALLOW_PRIVATE_NETWORK = os.getenv("GENAIL_ALLOW_PRIVATE_NETWORK", "false").lower() == "true"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _is_private_host(hostname: str) -> bool:
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        return True
    private_prefixes = (
        "10.",
        "172.16.", "172.17.", "172.18.", "172.19.", "172.2", "172.3",
        "192.168.",
    )
    return hostname.startswith(private_prefixes)


def _validate_url(url: str, allowed_hosts: List[str]) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"URL scheme not allowed: {parsed.scheme}")
    host = parsed.hostname or ""
    if not DEV_ALLOW_PRIVATE_NETWORK and _is_private_host(host):
        raise ValueError("URL host is not allowed")
    if allowed_hosts and host not in allowed_hosts:
        raise ValueError("URL host not in allowlist")


def _ipfs_to_gateway(ipfs_gateway: str, uri: str) -> str:
    if uri.startswith("ipfs://"):
        return ipfs_gateway.rstrip("/") + "/ipfs/" + uri[len("ipfs://"):]
    return uri


@dataclass
class ToolContext:
    api_base_url: str
    ipfs_gateway: str
    rpc_url: Optional[str]
    timeout_s: int
    allow_hosts: List[str]


class ToolRegistry:
    def __init__(self, context: ToolContext):
        self.context = context
        self.tool_calls = 0

    def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        _validate_url(url, self.context.allow_hosts)
        response = requests.request(method, url, timeout=self.context.timeout_s, **kwargs)
        response.raise_for_status()
        return response.json()

    def _ensure_limit(self) -> None:
        self.tool_calls += 1
        if self.tool_calls > TOOL_CALL_LIMIT:
            raise RuntimeError("tool call limit exceeded")

    def mmv_list_records(self, min_score_bps: int = 8000, limit: int = 50, offset: int = 0, program_id: Optional[str] = None) -> Any:
        self._ensure_limit()
        params = {
            "min_score_bps": min_score_bps,
            "limit": limit,
            "offset": offset,
        }
        if program_id:
            params["program_id"] = program_id
        url = f"{self.context.api_base_url.rstrip('/')}/records"
        payload = self._request("GET", url, params=params)
        return {
            "items": [
                {
                    "task_id": item.get("task_id") or item.get("id"),
                    "score_bps": item.get("score_bps") or item.get("score"),
                    "program_id": item.get("program_id"),
                }
                for item in (payload.get("items") or [])
            ],
            "limit": payload.get("limit", limit),
            "offset": payload.get("offset", offset),
        }

    def mmv_get_record(self, task_id: str) -> Any:
        self._ensure_limit()
        url = f"{self.context.api_base_url.rstrip('/')}/records/{task_id}"
        return self._request("GET", url)

    def mmv_get_receipt(self, task_id: str) -> Any:
        self._ensure_limit()
        url = f"{self.context.api_base_url.rstrip('/')}/receipts/{task_id}"
        payload = self._request("GET", url)
        return {
            "task_id": payload.get("task_id") or payload.get("id") or task_id,
            "status": payload.get("status"),
            "evidence_bundle_uri": payload.get("evidence_bundle_uri") or payload.get("bundle_uri"),
            "raw": payload,
        }

    def mmv_get_audit(self, task_id: str) -> Any:
        self._ensure_limit()
        url = f"{self.context.api_base_url.rstrip('/')}/audits/{task_id}"
        return self._request("GET", url)

    def mmv_fetch_evidence(self, bundle_uri: str) -> Any:
        self._ensure_limit()
        resolved = _ipfs_to_gateway(self.context.ipfs_gateway, bundle_uri)
        _validate_url(resolved, self.context.allow_hosts)
        response = requests.get(resolved, timeout=self.context.timeout_s)
        response.raise_for_status()
        return response.json()

    def mmv_verify_onchain(self, task_id: str, bundle_hash: str, chain_id: str, contract_address: str, rpc_url: Optional[str] = None) -> Any:
        self._ensure_limit()
        target_rpc = rpc_url or self.context.rpc_url
        if not target_rpc:
            raise RuntimeError("rpc_url not configured")
        _validate_url(target_rpc, self.context.allow_hosts)
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [
                {
                    "to": contract_address,
                    "data": "0x",
                },
                "latest",
            ],
            "id": 1,
        }
        response = requests.post(target_rpc, json=payload, timeout=self.context.timeout_s)
        response.raise_for_status()
        return {
            "task_id": task_id,
            "bundle_hash": bundle_hash,
            "chain_id": chain_id,
            "contract_address": contract_address,
            "rpc_result": response.json(),
        }


@dataclass
class ExecutionResult:
    stdout: str
    artifacts: Dict[str, Any]
    errors: List[str]
    tool_calls: int


class GenAILRunner:
    def __init__(self, tools: ToolRegistry, allow_llm: bool):
        self.tools = tools
        self.allow_llm = allow_llm
        self.variables: Dict[str, Any] = {}
        self.templates: Dict[str, str] = {}
        self.messages: List[Dict[str, str]] = []
        self.stdout_chunks: List[str] = []
        self.errors: List[str] = []

    def _append_stdout(self, text: str) -> None:
        if not text.endswith("\n"):
            text += "\n"
        existing = "".join(self.stdout_chunks)
        combined = existing + text
        if len(combined.encode("utf-8")) > MAX_OUTPUT_BYTES:
            raise RuntimeError("stdout limit exceeded")
        self.stdout_chunks.append(text)

    def _render_template(self, content: str) -> str:
        def replace(match: re.Match) -> str:
            key = match.group(1)
            value = self.variables.get(key, "")
            return str(value)

        return re.sub(r"\{\{\s*(\w+)\s*\}\}", replace, content)

    def _parse_value(self, token: str) -> Any:
        token = token.strip()
        if token.startswith("{") or token.startswith("["):
            return json.loads(token)
        if token.startswith('"') and token.endswith('"'):
            return token[1:-1]
        if token.isdigit():
            return int(token)
        if token.lower() in {"true", "false"}:
            return token.lower() == "true"
        if token.lower() == "null":
            return None
        return self.variables.get(token, token)

    def _handle_set(self, line: str) -> None:
        match = re.match(r"set\s+(\w+)\s*=\s*(.+)", line)
        if not match:
            raise ValueError("invalid set syntax")
        name, value = match.group(1), match.group(2)
        self.variables[name] = self._parse_value(value)

    def _handle_template(self, line: str) -> None:
        match = re.match(r"template\s+(\w+)\s*=\s*(.+)", line)
        if not match:
            raise ValueError("invalid template syntax")
        name, value = match.group(1), match.group(2)
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        self.templates[name] = value

    def _handle_prompt(self, line: str) -> None:
        match = re.match(r"prompt\s+(\w+)\s*=\s*(.+)", line)
        if not match:
            raise ValueError("invalid prompt syntax")
        name, value = match.group(1), match.group(2)
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        self.variables[name] = value

    def _handle_message(self, line: str) -> None:
        match = re.match(r"message\s+(\w+)\s*=\s*(.+)", line)
        if not match:
            raise ValueError("invalid message syntax")
        role, content = match.group(1), match.group(2)
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        self.messages.append({"role": role, "content": self._render_template(content)})

    def _handle_call(self, line: str) -> None:
        match = re.match(r"call\s+(\w+)\s+into\s+(\w+)(?:\s+with\s+(.+))?", line)
        if not match:
            raise ValueError("invalid call syntax")
        tool_name, target, args_blob = match.group(1), match.group(2), match.group(3)
        args = {}
        if args_blob:
            args_blob = args_blob.strip()
            if args_blob.startswith("{"):
                args = json.loads(args_blob)
            else:
                args = self.variables.get(args_blob, {})
        tool = getattr(self.tools, tool_name, None)
        if not tool:
            raise ValueError("tool not allowed")
        self.variables[target] = tool(**args)

    def _handle_print(self, line: str) -> None:
        match = re.match(r"print\s+(.+)", line)
        if not match:
            raise ValueError("invalid print syntax")
        content = match.group(1).strip()
        if content in self.variables:
            value = self.variables[content]
            self._append_stdout(json.dumps(value, indent=2, sort_keys=True))
            return
        if content in self.templates:
            self._append_stdout(self._render_template(self.templates[content]))
            return
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        self._append_stdout(self._render_template(content))

    def _handle_generate(self, line: str) -> None:
        if not self.allow_llm:
            raise RuntimeError("generate disabled; enable ALLOW_LLM_SUMMARIZATION")
        match = re.match(r"generate\s+(\w+)", line)
        if not match:
            raise ValueError("invalid generate syntax")
        target = match.group(1)
        generated = self._call_llm()
        self.variables[target] = generated
        self._append_stdout(generated)

    def _call_llm(self) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("GENAIL_MODEL", "gpt-4o-mini")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")
        payload = {
            "model": model,
            "messages": self.messages,
        }
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=self.tools.context.timeout_s,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def run(self, script: str) -> ExecutionResult:
        for raw_line in script.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                if line.startswith("set "):
                    self._handle_set(line)
                elif line.startswith("template "):
                    self._handle_template(line)
                elif line.startswith("prompt "):
                    self._handle_prompt(line)
                elif line.startswith("message "):
                    self._handle_message(line)
                elif line.startswith("call "):
                    self._handle_call(line)
                elif line.startswith("print "):
                    self._handle_print(line)
                elif line.startswith("generate "):
                    self._handle_generate(line)
                else:
                    raise ValueError("unsupported statement")
            except Exception as exc:  # noqa: BLE001
                self.errors.append(f"{line}: {exc}")
        stdout = "".join(self.stdout_chunks)
        return ExecutionResult(stdout=stdout, artifacts=self.variables, errors=self.errors, tool_calls=self.tools.tool_calls)


def _load_input() -> Dict[str, Any]:
    raw = sys.stdin.read()
    return json.loads(raw or "{}")


def main() -> None:
    payload = _load_input()
    script = payload.get("script", "")
    if len(script.encode("utf-8")) > SCRIPT_LIMIT_BYTES:
        raise SystemExit("script too large")
    vars_in = payload.get("vars") or {}
    tool_config = payload.get("tool_config") or {}
    allow_llm = bool(payload.get("allow_llm"))
    timeout_s = int(payload.get("timeout_s") or DEFAULT_TIMEOUT_S)

    api_base_url = tool_config.get("api_base_url", "").strip()
    ipfs_gateway = tool_config.get("ipfs_gateway", "").strip()
    rpc_url = tool_config.get("rpc_url")
    if not api_base_url or not ipfs_gateway:
        raise SystemExit("tool_config missing api_base_url or ipfs_gateway")

    allow_hosts = []
    for url in [api_base_url, ipfs_gateway, rpc_url]:
        if not url:
            continue
        parsed = urlparse(url)
        if parsed.hostname:
            allow_hosts.append(parsed.hostname)

    context = ToolContext(
        api_base_url=api_base_url,
        ipfs_gateway=ipfs_gateway,
        rpc_url=rpc_url,
        timeout_s=timeout_s,
        allow_hosts=allow_hosts,
    )
    tools = ToolRegistry(context)
    runner = GenAILRunner(tools, allow_llm=allow_llm)
    runner.variables.update(vars_in)
    result = runner.run(script)
    output = {
        "stdout": result.stdout,
        "artifacts": result.artifacts,
        "errors": result.errors,
        "tool_calls": result.tool_calls,
    }
    sys.stdout.write(json.dumps(output))


if __name__ == "__main__":
    started = _now_ms()
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        payload = {
            "stdout": "",
            "artifacts": {},
            "errors": [str(exc)],
            "tool_calls": 0,
        }
        sys.stdout.write(json.dumps(payload))
    finally:
        duration = _now_ms() - started
        if duration > DEFAULT_TIMEOUT_S * 1000:
            sys.stderr.write("genail runner exceeded timeout\n")
