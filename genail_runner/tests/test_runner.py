import json

from genail_runner.runner import ExecutionResult, GenAILRunner


class DummyTools:
    def __init__(self):
        self.tool_calls = 0

    def mmv_list_records(self, min_score_bps=8000, limit=50, offset=0, program_id=None):
        self.tool_calls += 1
        return {
            "items": [
                {"task_id": "task-1", "score_bps": min_score_bps},
            ],
            "limit": limit,
            "offset": offset,
            "program_id": program_id,
        }


def run_script(script: str) -> ExecutionResult:
    runner = GenAILRunner(DummyTools(), allow_llm=False)
    return runner.run(script)


def test_set_print_and_call():
    script = """
    set task_id = \"task-1\"
    call mmv_list_records into records with {\"min_score_bps\": 9000}
    print records
    print \"Task {{task_id}}\"
    """
    result = run_script(script)
    assert result.errors == []
    assert "task-1" in result.stdout
    parsed = json.loads(result.stdout.splitlines()[0])
    assert parsed["items"][0]["score_bps"] == 9000


def test_generate_disabled():
    script = "generate summary"
    result = run_script(script)
    assert any("generate disabled" in error for error in result.errors)
