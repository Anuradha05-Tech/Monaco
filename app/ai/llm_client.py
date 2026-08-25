import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


class LLMClient:

    def __init__(self, model="openai/gpt-oss-120b"):

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not set in .env"
            )

        self.client = Groq(
            api_key=api_key
        )

        self.model = model

    def review_code(self, code):

        system_prompt = """
You are a precise AI code reviewer.

Analyze the provided Python code.

ONLY report:
- Real security vulnerabilities
- Real bugs
- Clear code-quality problems

Do NOT report:
- Hypothetical problems
- Missing functionality that was not requested
- Generic optimization suggestions
- Performance concerns without evidence
- Personal style preferences

For every issue provide:

- category
- severity
- confidence
- line number if known
- short message
- short explanation
- short fix suggestion

Be concise.
Do not write an essay.
"""

        user_prompt = (
            "Review the following Python code.\n\n"
            "Only report important issues supported by the code.\n\n"
            "CODE:\n"
            f"{code}\n"
        )

        response = self.client.chat.completions.create(
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
            ],
            temperature=0.1
        )

        return response.choices[0].message.content