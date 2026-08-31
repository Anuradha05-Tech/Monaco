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

    def review_code(self, code, system_prompt=None):

        if system_prompt is None:
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
            "suggestion": "How to fix it",
            "rule_category": "hardcoded_secret",
            "variable_name": "API_KEY"
        }
    ]
}

Severity must be one of:

LOW
MEDIUM
HIGH
CRITICAL

Confidence must be a number between 0 and 1.

rule_category must be one of:
- hardcoded_secret
- command_injection
- eval_usage
- sql_injection
- other

If the finding does not map to any of the first four categories, you must return "other" explicitly. Do not leave it blank or null.

variable_name must be the name of the variable, function, or entity involved if applicable (e.g. for hardcoded secrets, the variable name), otherwise null.

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
            if finding.rule_category and finding.rule_category != "other":
                finding.rule_id = f"AI_{finding.rule_category.upper()}"

        return review