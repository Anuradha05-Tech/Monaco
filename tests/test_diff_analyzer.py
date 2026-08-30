import pytest
import git
from app.repository.diff_analyzer import DiffAnalyzer, InvalidGitRefError


@pytest.fixture
def temp_git_repo(tmp_path):
    repo = git.Repo.init(tmp_path)
    with repo.config_writer() as writer:
        writer.set_value("user", "name", "Test User")
        writer.set_value("user", "email", "test@example.com")

    # Create an initial commit with simple files to have a valid HEAD
    a_file = tmp_path / "a.py"
    a_file.write_text("line 1\nline 2\nline 3\n")

    b_file = tmp_path / "b.py"
    b_file.write_text("initial b\n")

    repo.index.add(["a.py", "b.py"])
    repo.index.commit("Initial commit")
    return repo, tmp_path


def test_diff_analyzer_added_lines_only(temp_git_repo):
    repo, tmp_path = temp_git_repo
    base_ref = repo.head.commit.hexsha

    # Modify a.py by appending lines
    a_file = tmp_path / "a.py"
    a_file.write_text("line 1\nline 2\nline 3\nline 4\nline 5\n")

    repo.index.add(["a.py"])
    repo.index.commit("Add lines")
    target_ref = repo.head.commit.hexsha

    analyzer = DiffAnalyzer(str(tmp_path))

    # Verify changed files and changed lines
    assert analyzer.get_changed_files(base_ref, target_ref) == ["a.py"]
    assert analyzer.get_changed_lines("a.py", base_ref, target_ref) == [4, 5]


def test_diff_analyzer_modified_lines(temp_git_repo):
    repo, tmp_path = temp_git_repo
    base_ref = repo.head.commit.hexsha

    # Modify a.py by replacing line 2
    a_file = tmp_path / "a.py"
    a_file.write_text("line 1\nline 2 modified\nline 3\n")

    repo.index.add(["a.py"])
    repo.index.commit("Modify line 2")
    target_ref = repo.head.commit.hexsha

    analyzer = DiffAnalyzer(str(tmp_path))
    assert analyzer.get_changed_files(base_ref, target_ref) == ["a.py"]
    assert analyzer.get_changed_lines("a.py", base_ref, target_ref) == [2]


def test_diff_analyzer_newly_added_file(temp_git_repo):
    repo, tmp_path = temp_git_repo
    base_ref = repo.head.commit.hexsha

    # Create new file c.py
    c_file = tmp_path / "c.py"
    c_file.write_text("new file line 1\nnew file line 2\n")

    repo.index.add(["c.py"])
    repo.index.commit("Add c.py")
    target_ref = repo.head.commit.hexsha

    analyzer = DiffAnalyzer(str(tmp_path))
    assert sorted(analyzer.get_changed_files(base_ref, target_ref)) == ["c.py"]
    assert analyzer.get_changed_lines("c.py", base_ref, target_ref) == [1, 2]


def test_diff_analyzer_deleted_file(temp_git_repo):
    repo, tmp_path = temp_git_repo
    base_ref = repo.head.commit.hexsha

    # Delete b.py
    b_file = tmp_path / "b.py"
    b_file.unlink()

    repo.index.remove(["b.py"])
    repo.index.commit("Delete b.py")
    target_ref = repo.head.commit.hexsha

    analyzer = DiffAnalyzer(str(tmp_path))
    # Deleted file b.py should be excluded from get_changed_files
    assert analyzer.get_changed_files(base_ref, target_ref) == []
    assert analyzer.get_changed_lines("b.py", base_ref, target_ref) == []


def test_diff_analyzer_no_changes(temp_git_repo):
    repo, tmp_path = temp_git_repo
    base_ref = repo.head.commit.hexsha

    # Make a commit without changes
    repo.index.commit("Dummy commit")
    target_ref = repo.head.commit.hexsha

    analyzer = DiffAnalyzer(str(tmp_path))
    assert analyzer.get_changed_files(base_ref, target_ref) == []
    assert analyzer.get_changed_lines("a.py", base_ref, target_ref) == []


def test_diff_analyzer_invalid_ref(temp_git_repo):
    repo, tmp_path = temp_git_repo
    analyzer = DiffAnalyzer(str(tmp_path))

    with pytest.raises(InvalidGitRefError):
        analyzer.get_changed_files("nonexistent-ref", "HEAD")

    with pytest.raises(InvalidGitRefError):
        analyzer.get_changed_files("HEAD", "nonexistent-ref")

    with pytest.raises(InvalidGitRefError):
        analyzer.get_changed_lines("a.py", "nonexistent-ref", "HEAD")


def test_diff_analyzer_renamed_file(tmp_path):
    repo = git.Repo.init(tmp_path)
    with repo.config_writer() as writer:
        writer.set_value("user", "name", "Test User")
        writer.set_value("user", "email", "test@example.com")

    # Commit initial file
    old_file = tmp_path / "old_name.py"
    old_file.write_text("x = 1\n")
    repo.index.add(["old_name.py"])
    repo.index.commit("Initial commit")
    base_ref = repo.head.commit.hexsha

    # Rename it using git mv command via GitPython wrapper
    repo.git.mv("old_name.py", "new_name.py")
    repo.index.commit("Rename file")
    target_ref = repo.head.commit.hexsha

    analyzer = DiffAnalyzer(str(tmp_path))
    changed_files = analyzer.get_changed_files(base_ref, target_ref)

    assert "new_name.py" in changed_files
    assert "old_name.py" not in changed_files


def test_diff_analyzer_binary_file(tmp_path):
    repo = git.Repo.init(tmp_path)
    with repo.config_writer() as writer:
        writer.set_value("user", "name", "Test User")
        writer.set_value("user", "email", "test@example.com")

    # Commit initial binary file
    bin_file = tmp_path / "data.bin"
    bin_file.write_bytes(b"\x00\x00\x00")
    repo.index.add(["data.bin"])
    repo.index.commit("Add binary file")
    base_ref = repo.head.commit.hexsha

    # Modify binary file
    bin_file.write_bytes(b"\x00\x00\x00\x01\x02")
    repo.index.add(["data.bin"])
    repo.index.commit("Modify binary file")
    target_ref = repo.head.commit.hexsha

    analyzer = DiffAnalyzer(str(tmp_path))
    # Should not raise exception and return empty list of lines
    assert analyzer.get_changed_lines("data.bin", base_ref, target_ref) == []

