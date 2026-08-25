from app.ai.llm_client import LLMClient


code = """
def login(username, password):

    query = "SELECT * FROM users WHERE username = '" + username + "'"

    return query
"""


llm = LLMClient()

print("\n==============================")
print("       AI CODE REVIEW")
print("==============================\n")

review = llm.review_code(code)

print(review)