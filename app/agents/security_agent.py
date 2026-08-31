from app.models.finding import Finding
from app.engine.review_engine import ReviewEngine

class SecurityAgent:
    """
    Wraps the existing static analyzer, data-flow analyzer, and AI reviewer
    to perform security-focused review checks.
    """
    def __init__(self, review_engine: ReviewEngine):
        self.review_engine = review_engine

    def analyze(self, file_path: str, code: str) -> list[Finding]:
        # Run all three existing analysis layers
        static_findings = self.review_engine.analyzer.analyze(code)["findings"]
        data_flow_findings = self.review_engine.data_flow_analyzer.analyze(code)
        
        # Guard LLM call to handle potential None or missing LLM gracefully
        ai_findings = []
        if self.review_engine.llm:
            try:
                security_prompt = """
You are a precise AI code-review engine focused EXCLUSIVELY on security vulnerabilities.

Analyze Python code for:
- Real security vulnerabilities (e.g. command injection, hardcoded secrets, unsafe deserialization, auth/access control issues, unsafe use of eval/exec/subprocess).

Do NOT report code quality, complexity, style, or documentation issues.

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
                ai_review = self.review_engine.llm.review_code(code, system_prompt=security_prompt)
                if ai_review and hasattr(ai_review, "findings"):
                    ai_findings = ai_review.findings
            except Exception:
                pass

        combined = []
        combined.extend(static_findings)
        combined.extend(data_flow_findings)
        combined.extend(ai_findings)

        security_findings = []
        for finding in combined:
            is_sec = False
            # Check if category is security or rule_id indicates a security finding
            if getattr(finding, "category", None) == "security":
                is_sec = True
            elif finding.rule_id and (finding.rule_id.startswith("SEC") or finding.rule_id.startswith("FLOW")):
                is_sec = True
            
            # Exclude code quality or complexity issues that may be miscategorized
            if is_sec and finding.message:
                msg_lower = finding.message.lower()
                exclude_keywords = ["except", "complexity", "lines long", "docstring", "parameter", "nesting", "nested"]
                if any(kw in msg_lower for kw in exclude_keywords):
                    is_sec = False
            
            if is_sec:
                finding.file = file_path
                finding.category = "security"
                
                # Populate sources list appropriately
                if finding.sources is None:
                    finding.sources = []
                if not finding.sources:
                    if finding.source:
                        finding.sources = [finding.source]
                    else:
                        finding.sources = ["static_analyzer"]
                security_findings.append(finding)

        return security_findings
