from app.analyzer.python_analyzer import PythonAnalyzer
from app.ai.llm_client import LLMClient
from app.engine.deduplicator import FindingDeduplicator
from app.engine.ranker import FindingRanker
from app.engine.validator import FindingValidator

class ReviewEngine:

    def __init__(self):

        self.analyzer = PythonAnalyzer()

        self.llm = LLMClient()

        self.deduplicator = FindingDeduplicator()

        self.ranker = FindingRanker()

        self.validator = FindingValidator()

    def review(self, code):

        # --------------------------------
        # STEP 1: Static analysis
        # --------------------------------

        static_result = self.analyzer.analyze(code)

        static_findings = static_result["findings"]

        # --------------------------------
        # STEP 2: AI analysis
        # --------------------------------

        ai_review = self.llm.review_code(code)

        ai_findings = ai_review.findings

        # --------------------------------
        # STEP 3: Combine
        # --------------------------------

        all_findings = []

        all_findings.extend(static_findings)

        all_findings.extend(ai_findings)

        # --------------------------------
        # STEP 4: Deduplicate + merge
        # --------------------------------

        unique_findings = (
            self.deduplicator.deduplicate(
                all_findings
            )
        )
        
        # --------------------------------
        # STEP 5: Validate findings
        # --------------------------------

        validated_findings = []

        for finding in unique_findings:

            is_valid = self.validator.validate(
                code,
                finding
            )

            if is_valid:

                validated_findings.append(
                    finding
                )

        # --------------------------------
        # STEP 6: Rank
        # --------------------------------

        ranked_findings = self.ranker.rank(
            validated_findings
        )

        return ranked_findings