import pytest
from app.repository.dependency_graph import DependencyGraphBuilder


def test_dependency_graph_builder_simple_chain(tmp_path):
    # Setup files: a.py -> b.py -> c.py
    a_file = tmp_path / "a.py"
    b_file = tmp_path / "b.py"
    c_file = tmp_path / "c.py"

    a_file.write_text("import b")
    b_file.write_text("import c")
    c_file.write_text("x = 42")

    builder = DependencyGraphBuilder()
    graph = builder.build(str(tmp_path))

    assert graph == {
        "a.py": ["b.py"],
        "b.py": ["c.py"],
        "c.py": []
    }


def test_dependency_graph_builder_stdlib_ignored(tmp_path):
    # Setup file that imports stdlib/third-party modules
    a_file = tmp_path / "a.py"
    a_file.write_text("import os\nimport sys\nimport requests")

    builder = DependencyGraphBuilder()
    graph = builder.build(str(tmp_path))

    assert graph == {
        "a.py": []
    }


def test_dependency_graph_builder_no_imports(tmp_path):
    # Setup file with no imports at all
    a_file = tmp_path / "a.py"
    a_file.write_text("def hello():\n    return 'world'")

    builder = DependencyGraphBuilder()
    graph = builder.build(str(tmp_path))

    assert graph == {
        "a.py": []
    }


def test_dependency_graph_builder_circular_imports(tmp_path):
    # Setup circular imports: a.py -> b.py, b.py -> a.py
    a_file = tmp_path / "a.py"
    b_file = tmp_path / "b.py"

    a_file.write_text("import b")
    b_file.write_text("import a")

    builder = DependencyGraphBuilder()
    graph = builder.build(str(tmp_path))

    assert graph == {
        "a.py": ["b.py"],
        "b.py": ["a.py"]
    }


def test_dependency_graph_builder_syntax_error_handled_gracefully(tmp_path, caplog):
    # Setup a file with bad syntax and a normal file
    a_file = tmp_path / "a.py"
    b_file = tmp_path / "b.py"

    a_file.write_text("import b")
    b_file.write_text("def error_func(")

    builder = DependencyGraphBuilder()
    graph = builder.build(str(tmp_path))

    # b.py should be skipped and a warning logged, but build shouldn't crash
    # a.py should still resolve imports (b.py exists, so it's resolved, but b.py itself is not in the graph keys)
    assert "a.py" in graph
    assert "b.py" not in graph
    assert graph["a.py"] == ["b.py"]


    # Check that warning is logged
    import logging
    warnings = [rec.message for rec in caplog.records if rec.levelno == logging.WARNING]
    assert any("Syntax error in file b.py" in w for w in warnings)


def test_dependency_graph_builder_relative_imports(tmp_path):
    # Setup directory structure for double-dot relative import
    app_dir = tmp_path / "app"
    feature_dir = app_dir / "feature"
    sub_dir = feature_dir / "sub"

    sub_dir.mkdir(parents=True, exist_ok=True)

    (app_dir / "__init__.py").write_text("")
    (feature_dir / "__init__.py").write_text("")
    (sub_dir / "__init__.py").write_text("")

    pkg_file = feature_dir / "pkg.py"
    pkg_file.write_text("x = 1")

    mod_file = sub_dir / "mod.py"
    mod_file.write_text("from ..pkg import thing")

    # Setup directory structure for single-dot relative import
    a_file = feature_dir / "a.py"
    b_file = feature_dir / "b.py"

    a_file.write_text("from . import b")
    b_file.write_text("y = 2")

    builder = DependencyGraphBuilder()
    graph = builder.build(str(tmp_path))

    assert graph["app/feature/sub/mod.py"] == ["app/feature/pkg.py"]
    assert graph["app/feature/a.py"] == ["app/feature/b.py"]

