from app.models.finding import Finding


class FindingRanker:

    SEVERITY_SCORES = {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4
    }

    def calculate_score(
        self,
        finding: Finding
    ):

        severity_score = self.SEVERITY_SCORES[
            finding.severity.value
        ]

        confidence = finding.confidence

        source_count = len(
            finding.sources
        )

        if source_count >= 2:
            evidence_multiplier = 1.2
        else:
            evidence_multiplier = 1.0

        score = (
            severity_score
            * confidence
            * evidence_multiplier
        )

        return score

    def rank(
        self,
        findings: list[Finding]
    ):

        ranked_findings = []

        for finding in findings:

            score = self.calculate_score(
                finding
            )

            ranked_findings.append(
                (score, finding)
            )

        ranked_findings.sort(
            key=lambda item: item[0],
            reverse=True
        )

        return [
            finding
            for score, finding
            in ranked_findings
        ]