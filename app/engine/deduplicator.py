from app.models.finding import Finding


class FindingDeduplicator:

    LINE_DISTANCE = 3

    def are_duplicates(
        self,
        first: Finding,
        second: Finding
    ):

        if first.category != second.category:
            return False

        if (
            first.line is not None
            and second.line is not None
        ):

            distance = abs(
                first.line - second.line
            )

            if distance > self.LINE_DISTANCE:
                return False

        first_text = (
            first.message.lower()
            + " "
            + (first.explanation or "").lower()
        )

        second_text = (
            second.message.lower()
            + " "
            + (second.explanation or "").lower()
        )

        keywords = [
            "eval",
            "exec",
            "subprocess",
            "secret",
            "api key",
            "password",
            "sql injection",
            "hardcoded"
        ]

        for keyword in keywords:

            if (
                keyword in first_text
                and keyword in second_text
            ):

                return True

        return False

    def merge(
        self,
        first: Finding,
        second: Finding
    ):

        # Prefer the more severe finding.

        severity_order = {
            "LOW": 1,
            "MEDIUM": 2,
            "HIGH": 3,
            "CRITICAL": 4
        }

        first_score = severity_order[
            first.severity.value
        ]

        second_score = severity_order[
            second.severity.value
        ]

        if second_score > first_score:
            primary = second
            secondary = first

        else:
            primary = first
            secondary = second

        # Keep the highest confidence.

        primary.confidence = max(
            first.confidence,
            second.confidence
        )

        # Keep a rule ID if one exists.

        if primary.rule_id is None:

            primary.rule_id = (
                secondary.rule_id
            )

        # Keep the best explanation.

        if (
            not primary.explanation
            and secondary.explanation
        ):

            primary.explanation = (
                secondary.explanation
            )

        # Keep the best suggestion.

        if (
            not primary.suggestion
            and secondary.suggestion
        ):

            primary.suggestion = (
                secondary.suggestion
            )

        # Record evidence sources.

        sources = set()

        sources.add(first.source)
        sources.add(second.source)

        for source in first.sources:
            sources.add(source)

        for source in second.sources:
            sources.add(source)

        primary.sources = list(sources)

        return primary

    def deduplicate(self, findings):

        unique_findings = []

        for finding in findings:

            duplicate_index = None

            for index, existing in enumerate(
                unique_findings
            ):

                if self.are_duplicates(
                    existing,
                    finding
                ):

                    duplicate_index = index

                    break

            if duplicate_index is None:

                if not finding.sources:

                    finding.sources = [
                        finding.source
                    ]

                unique_findings.append(
                    finding
                )

            else:

                existing = unique_findings[
                    duplicate_index
                ]

                merged = self.merge(
                    existing,
                    finding
                )

                unique_findings[
                    duplicate_index
                ] = merged

        return unique_findings