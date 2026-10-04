import json
from pathlib import Path

import pytest

from agentaudit.chunking import Source, wrap_long_lines
from agentaudit.packet import write_packet


def make_sources():
    paper = "\n".join(
        ["# Title", "We introduce a benchmark of clinical tasks for language-model agents.",
         "Each task was run five times per model with independent seeds and the mean is reported.",
         "The tasks use de-identified records from a public hospital database."]
        + [f"Filler paragraph {i} about nothing in particular, covering unrelated material." * 3 for i in range(60)]
        + ["Appendix A: The temperature was set to 0.7."])
    readme = "# Repo\nRun `python main.py`. The agent can call tools: lookup(patient_id) reads, order(med) writes."
    code = "\n".join([
        'SYSTEM_PROMPT = "You are a doctor agent. Use the tools below."',
        'TOOLS = [{"type": "function", "function": {"name": "lookup", "parameters": {"patient_id": "str"}}}]',
        "def lookup(patient_id):",
        "    return db[patient_id]",
    ])
    return [Source("S1", "arxiv/0000.00000v1.html", wrap_long_lines(paper)),
            Source("S2", "README.md", wrap_long_lines(readme)),
            Source("S4", "agent/tools.py", wrap_long_lines(code))]


@pytest.fixture()
def run_dir(tmp_path):
    write_packet(tmp_path, "toy", make_sources(), {"name": "toy", "built_utc": "2026-01-01T00:00:00Z"})
    return tmp_path
