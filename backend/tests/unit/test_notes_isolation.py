from unittest.mock import Mock

from src.agent.tools.get_progress import GetProgressTool
from src.agent.tools.save_note import SaveNoteTool
from src.memory.long_term import LongTermMemory


def test_notes_queries_always_use_the_bound_identity():
    vector = Mock()
    vector.user_memory.query.return_value = {"documents": [["own-note"]]}
    memory = LongTermMemory(vector, lambda text: [1, 0])
    assert memory.search_notes("B", "question") == ["own-note"]
    assert vector.user_memory.query.call_args.kwargs["where"] == {"user_id": "B"}


def test_llm_cannot_override_bound_tool_identity():
    memory, progress = Mock(), Mock()
    note_tool = SaveNoteTool(memory, "B")
    progress_tool = GetProgressTool(progress, "B")
    note_tool.safe_run(note="text", user_id="A")
    progress_tool.safe_run(user_id="A")
    memory.save_note.assert_not_called()
    progress.get_summary.assert_not_called()
