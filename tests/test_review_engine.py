from app.engine.review_engine import ReviewEngine


def test_review_engine_returns_findings():

    code = """
user_input = input("Enter input")

result = eval(user_input)
"""

    engine = ReviewEngine()

    findings = engine.review(code)

    assert len(findings) >= 1