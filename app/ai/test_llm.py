from app.ai.llm_client import OllamaClient


code = """
def login(username, password):

    query = "SELECT * FROM users WHERE username = '" + username + "'"

    return query
"""


llm = OllamaClient()

review = llm.review_code(code)

print("\n==============================")
print("       AI CODE REVIEW")
print("==============================\n")

print(review)