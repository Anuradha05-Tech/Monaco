from app.analyzer.python_analyzer import PythonAnalyzer
from app.analyzer.data_flow_analyzer import DataFlowAnalyzer

from app.ai.llm_client import LLMClient

from app.engine.deduplicator import FindingDeduplicator
from app.engine.ranker import FindingRanker

from app.engine.validator import (
    FindingValidator,
    ValidationResult
)


class ReviewEngine:

    def __init__(self):

        # Static AST analyzer
        self.analyzer = PythonAnalyzer()

        # Data-flow / taint analyzer
        self.data_flow_analyzer = DataFlowAnalyzer()

        # AI analyzer
        self.llm = LLMClient()

        # Finding processing
        self.deduplicator = FindingDeduplicator()

        self.validator = FindingValidator()

        self.ranker = FindingRanker()

    def review(self, code):

        # --------------------------------
        # STEP 1: Static analysis
        # --------------------------------

        static_result = self.analyzer.analyze(code)

        static_findings = static_result["findings"]

        # --------------------------------
        # STEP 2: Data-flow analysis
        # --------------------------------

        data_flow_findings = (
            self.data_flow_analyzer.analyze(code)
        )

        # --------------------------------
        # STEP 3: AI analysis
        # --------------------------------

        ai_review = self.llm.review_code(code)

        ai_findings = ai_review.findings

        # --------------------------------
        # STEP 4: Combine all findings
        # --------------------------------

        all_findings = []

        all_findings.extend(
            static_findings
        )

        all_findings.extend(
            data_flow_findings
        )

        all_findings.extend(
            ai_findings
        )

        # --------------------------------
        # STEP 5: Deduplicate + merge
        # --------------------------------

        unique_findings = (
            self.deduplicator.deduplicate(
                all_findings
            )
        )

        # --------------------------------
        # STEP 6: Validate
        # --------------------------------

        validated_findings = []

        for finding in unique_findings:

            validation_result = (
                self.validator.validate(
                    code,
                    finding
                )
            )

            if (
                validation_result
                == ValidationResult.VALID
            ):

                validated_findings.append(
                    finding
                )

        # --------------------------------
        # STEP 7: Rank
        # --------------------------------

        ranked_findings = (
            self.ranker.rank(
                validated_findings
            )
        )

        return ranked_findings