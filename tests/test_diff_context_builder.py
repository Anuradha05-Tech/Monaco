import pytest
import git
from app.repository.diff_analyzer import DiffAnalyzer
from app.repository.dependency_graph import DependencyGraphBuilder
from app.repository.diff_context_builder import DiffContextBuilder


def test_diff_context_builder(tmp_path):
    repo = git.Repo.init(tmp_path)
    with repo.config_writer() as writer:
        writer.set_value("user", "name", "Test User")
        writer.set_value("user", "email", "test@example.com")

    # Create initial files
    a_file = tmp_path / "a.py"
    b_file = tmp_path / "b.py"
    c_file = tmp_path / "c.py"

    a_file.write_text("import b\n")
    b_file.write_text("import c\n")
    c_file.write_text("x = 42\n")

    repo.index.add(["a.py", "b.py", "c.py"])
    repo.index.commit("Initial commit")
    base_ref = repo.head.commit.hexsha

    # Modify a.py
    a_file.write_text("import b\nprint('hello')\n")
    repo.index.add(["a.py"])
    repo.index.commit("Modify a.py")
    target_ref = repo.head.commit.hexsha

    graph_builder = DependencyGraphBuilder()
    diff_analyzer = DiffAnalyzer(str(tmp_path))
    context_builder = DiffContextBuilder(graph_builder, diff_analyzer)

    context = context_builder.build_review_context(base_ref, target_ref)

    assert context["changed_files"] == ["a.py"]
    assert context["changed_lines"] == {"a.py": [2]}
    assert context["related_files"] == {"a.py": ["b.py"]}
