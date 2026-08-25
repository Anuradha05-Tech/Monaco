import ollama


class OllamaClient:

    def __init__(self, model="llama3.2"):
        self.model = model

    def review_code(self, code):

        system_prompt = """
You are an expert software engineer and code reviewer.

Analyze the provided Python code.

Look for:

1. Security vulnerabilities
2. Bugs
3. Code quality problems
4. Performance problems
5. Maintainability problems

Only report issues that are supported by the code.

For every important issue, explain:

- What the problem is
- Why it matters
- How it could be improved
"""

        user_prompt = f"""
Review the following Python code:

```python
{code}
"""

        response = ollama.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        )

        return response["message"]["content"]


if __name__ == "__main__":

    client = OllamaClient()

    result = client.review_code("print('hello world')")

    print(result)