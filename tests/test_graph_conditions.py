from app.graph.conditions import has_changed_python_files, check_validation_quality

def test_has_changed_python_files():
    # Case 1: Changed files include python files
    state_with_py = {
        "pr_context": {
            "changed_files": ["README.md", "app/main.py", "tests/test_main.py"]
        }
    }
    assert has_changed_python_files(state_with_py) == "analyze"

    # Case 2: Changed files do not include python files
    state_no_py = {
        "pr_context": {
            "changed_files": ["README.md", "assets/logo.png", "docker-compose.yml"]
        }
    }
    assert has_changed_python_files(state_no_py) == "skip_to_end"

    # Case 3: Empty changed files list
    state_empty = {
        "pr_context": {
            "changed_files": []
        }
    }
    assert has_changed_python_files(state_empty) == "skip_to_end"

def test_check_validation_quality_boundary():
    # Case 1: Rejection ratio is strictly above 0.5 (e.g. 0.51)
    state_above = {"rejection_ratio": 0.51}
    assert check_validation_quality(state_above) == "flag_review"

    # Case 2: Rejection ratio is strictly below 0.5 (e.g. 0.49)
    state_below = {"rejection_ratio": 0.49}
    assert check_validation_quality(state_below) == "rank"

    # Case 3: Rejection ratio is exactly at 0.5 boundary
    state_exactly = {"rejection_ratio": 0.50}
    assert check_validation_quality(state_exactly) == "rank"
