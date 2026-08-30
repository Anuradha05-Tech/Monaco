from app.engine.review_engine import ReviewEngine


def test_review_engine_returns_findings():

    code = """
user_input = input("Enter input")

result = eval(user_input)
"""

    engine = ReviewEngine()

    findings = engine.review(code)

    assert len(findings) >= 1


def test_review_engine_preserves_close_security_findings():

    code = """import subprocess

def run_backup(filename):
    # BUG: shell=True + unsanitized input = command injection
    subprocess.run(f"tar -cvf backup.tar {filename}", shell=True)

API_KEY = "sk-hardcoded-secret-12345"  # BUG: hardcoded secret
"""

    engine = ReviewEngine()
    findings = engine.review(code)

    rule_ids = {f.rule_id for f in findings}
    assert "SEC002" in rule_ids
    assert "SEC003" in rule_ids