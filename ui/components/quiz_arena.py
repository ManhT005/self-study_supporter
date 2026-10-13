from apps.streamlit_legacy.components.quiz_arena import render_quiz_arena as render_quiz_arena
from study_supporter.ai.assessment.legacy_parser import (
    parse_quiz_from_text as _parse_quiz_from_text,
)

__all__ = ["render_quiz_arena", "_parse_quiz_from_text"]
