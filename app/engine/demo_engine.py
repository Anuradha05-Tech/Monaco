from app.engine.review_engine import ReviewEngine


code = """
import subprocess

API_KEY = "secret-value"

user_input = input("Enter command")

result = eval(user_input)

subprocess.run(user_input)
"""


engine = ReviewEngine()

findings = engine.review(code)


print("\n==============================")
print("       MONACO CODE REVIEW")
print("==============================\n")

print(f"Total findings: {len(findings)}\n")


for index, finding in enumerate(findings, start=1):

    print(f"Finding #{index}")
    print("------------------------------")

    print(f"Source:      {finding.source}")
    print(f"Sources:     {finding.sources}")
    print(f"Rule ID:     {finding.rule_id}")
    print(f"Category:    {finding.category}")
    print(f"Severity:    {finding.severity.value}")
    print(f"Confidence:  {finding.confidence}")
    print(f"Line:        {finding.line}")
    print(f"Message:     {finding.message}")

    print()