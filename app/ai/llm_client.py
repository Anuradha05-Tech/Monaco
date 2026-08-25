import json
import os

from dotenv import load_dotenv
from groq import Groq

from app.models.ai_review import AIReview


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
You are a precise AI code-review engine.

Analyze Python code for:

- Real security vulnerabilities
- Real bugs
- Clear code-quality problems

Do NOT report:

- Hypothetical problems
- Generic suggestions
- Performance concerns without evidence
- Missing functionality that was not requested
- Personal style preferences

Return ONLY valid JSON.

The JSON must have exactly this structure:

{
    "findings": [
        {
            "category": "security",
            "severity": "HIGH",
            "confidence": 0.95,
            "line": 3,
            "message": "Short description",
            "explanation": "Why this is a real issue",
            "suggestion": "How to fix it"
        }
    ]
}

Severity must be one of:

LOW
MEDIUM
HIGH
CRITICAL

Confidence must be a number between 0 and 1.

If there are no important issues, return:

{
    "findings": []
}

Do not include markdown.
Do not include ```json.
Do not include any text outside the JSON.
"""

        user_prompt = (
            "Analyze this Python code.\n\n"
            f"{code}"
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

        raw_response = response.choices[0].message.content

        if not raw_response:
            raise ValueError(
                "The LLM returned an empty response."
            )

        data = json.loads(raw_response)

        review = AIReview.model_validate(data)

        for finding in review.findings:
            finding.source = "ai"

        return review