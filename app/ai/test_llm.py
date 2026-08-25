from app.ai.llm_client import LLMClient


code = """
def login(username, password):

    query = "SELECT * FROM users WHERE username = '" + username + "'"

    return query
"""


llm = LLMClient()

review = llm.review_code(code)


print("\n==============================")
print("       AI CODE REVIEW")
print("==============================\n")


print(f"Total findings: {len(review.findings)}\n")


for index, finding in enumerate(review.findings, start=1):

    print(f"Finding #{index}")
    print("------------------------------")

    print(f"Rule ID:     {finding.rule_id}")
    print(f"Category:    {finding.category}")
    print(f"Severity:    {finding.severity.value}")
    print(f"Confidence:  {finding.confidence}")
    print(f"Line:        {finding.line}")
    print(f"Message:     {finding.message}")
    print(f"Explanation: {finding.explanation}")
    print(f"Suggestion:  {finding.suggestion}")
    print(f"Source:      {finding.source}")

    print()