from app.repository.context_retriever import ContextRetriever


def test_context_retriever_neighbors_depth_1():
    # Graph: A -> B -> C
    graph = {
        "a.py": ["b.py"],
        "b.py": ["c.py"],
        "c.py": []
    }
    retriever = ContextRetriever(graph)

    assert retriever.get_related_files("a.py", depth=1) == ["b.py"]
    assert retriever.get_related_files("b.py", depth=1) == ["a.py", "c.py"]
    assert retriever.get_related_files("c.py", depth=1) == ["b.py"]


def test_context_retriever_depth_2():
    # Graph: A -> B -> C
    graph = {
        "a.py": ["b.py"],
        "b.py": ["c.py"],
        "c.py": []
    }
    retriever = ContextRetriever(graph)

    assert retriever.get_related_files("a.py", depth=2) == ["b.py", "c.py"]
    assert retriever.get_related_files("c.py", depth=2) == ["a.py", "b.py"]


def test_context_retriever_circular_and_complex():
    # Graph:
    # A -> B
    # B -> A, C
    # C -> D
    # D -> B
    graph = {
        "a.py": ["b.py"],
        "b.py": ["a.py", "c.py"],
        "c.py": ["d.py"],
        "d.py": ["b.py"]
    }
    retriever = ContextRetriever(graph)

    # Depth=1 for B: A, C, D (D imports B, B imports C/A)
    assert retriever.get_related_files("b.py", depth=1) == ["a.py", "c.py", "d.py"]
    # Depth=2 for A: B (depth 1), C (depth 2), D (depth 2)
    assert retriever.get_related_files("a.py", depth=2) == ["b.py", "c.py", "d.py"]


def test_context_retriever_unknown_file():
    graph = {
        "a.py": ["b.py"],
        "b.py": []
    }
    retriever = ContextRetriever(graph)

    assert retriever.get_related_files("unknown.py", depth=1) == []
    assert retriever.get_related_files("unknown.py", depth=2) == []
