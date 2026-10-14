import pytest
from pydantic import ValidationError

from study_supporter.domain.knowledge_graph import ConceptGraph


def test_unknown_edge_cannot_create_an_invented_node():
    with pytest.raises(ValidationError, match="unknown concept"):
        ConceptGraph(
            nodes=[{"id": "a", "label": "A"}],
            edges=[{"source": "a", "target": "missing"}],
        )
