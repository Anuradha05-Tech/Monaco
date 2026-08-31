import re
import unicodedata
from app.models.finding import Finding


def normalize_text(text: str) -> str:
    # Normalize unicode to compatibility form
    t = unicodedata.normalize("NFKC", text.lower())
    # Remove all whitespace, hyphens, underscores, and other dashes/punctuations
    t = re.sub(r'[\s_\-\u2010-\u2015\u2212]+', '', t)
    return t


def extract_variable_name(finding: Finding) -> str | None:
    if finding.variable_name:
        return finding.variable_name.lower()
    
    # Fallback to parsing from message text using regex
    match = re.search(r"variable\s+'([^']+)'", finding.message)
    if match:
        return match.group(1).lower()
        
    match_ai = re.search(r"variable\s+'([^']+)'", finding.message, re.IGNORECASE)
    if match_ai:
        return match_ai.group(1).lower()
        
    return None


class FindingDeduplicator:

    LINE_DISTANCE = 3

    def are_rule_ids_compatible(self, id1: str | None, id2: str | None) -> bool:
        if id1 is None or id2 is None:
            return True
        if id1 == id2:
            return True
        # NOTE: New analyzer rule pairs describing the same underlying issue 
        # must be manually added here. This is a deliberate, documented 
        # tradeoff to ensure precision, not an oversight.
        equivalents = {
            ("FLOW001", "SEC001"),
            ("SEC001", "FLOW001"),
            ("FLOW002", "SEC003"),
            ("SEC003", "FLOW002"),
            # AI structured rule equivalences
            ("AI_HARDCODED_SECRET", "SEC002"),
            ("SEC002", "AI_HARDCODED_SECRET"),
            ("AI_COMMAND_INJECTION", "SEC003"),
            ("SEC003", "AI_COMMAND_INJECTION"),
            ("AI_COMMAND_INJECTION", "FLOW002"),
            ("FLOW002", "AI_COMMAND_INJECTION"),
            ("AI_EVAL_USAGE", "SEC001"),
            ("SEC001", "AI_EVAL_USAGE"),
            ("AI_EVAL_USAGE", "FLOW001"),
            ("FLOW001", "AI_EVAL_USAGE"),
        }
        
        pair = tuple(sorted([id1, id2]))
        return pair in equivalents

    def are_duplicates(
        self,
        first: Finding,
        second: Finding
    ):

        if first.category != second.category:
            return False

        if not self.are_rule_ids_compatible(first.rule_id, second.rule_id):
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

        # Specific named entity rules (e.g. SEC002 / AI_HARDCODED_SECRET)
        named_entity_rules = {"SEC002", "AI_HARDCODED_SECRET"}
        is_first_secret = (first.rule_id in named_entity_rules) or (first.rule_category == "hardcoded_secret")
        is_second_secret = (second.rule_id in named_entity_rules) or (second.rule_category == "hardcoded_secret")
        
        if is_first_secret or is_second_secret:
            first_entity = extract_variable_name(first)
            second_entity = extract_variable_name(second)
            if first_entity is not None and second_entity is not None:
                if first_entity != second_entity:
                    return False

        # If both findings have structured rule IDs (i.e. not None),
        # we rely entirely on the rule ID compatibility check and line proximity.
        if first.rule_id is not None and second.rule_id is not None:
            return True

        # Last-resort fallback for cases where at least one finding has no rule_id.
        # This fallback is inherently unreliable and known to miss cases like Unicode
        # punctuation variants, so it is a narrow safety net, not the primary mechanism.
        first_text = normalize_text(
            first.message
            + " "
            + (first.explanation or "")
        )

        second_text = normalize_text(
            second.message
            + " "
            + (second.explanation or "")
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
            normalized_kw = normalize_text(keyword)
            if (
                normalized_kw in first_text
                and normalized_kw in second_text
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

        if primary.message != secondary.message:
            p_lower = primary.message.lower()
            s_lower = secondary.message.lower()
            if p_lower not in s_lower and s_lower not in p_lower:
                primary.message = f"{primary.message} ({secondary.message})"


        # Keep a rule ID if one exists. Prefer static/data-flow rule IDs (SEC/FLOW) over generic AI ones.
        if primary.rule_id is None:
            primary.rule_id = secondary.rule_id
        elif primary.rule_id.startswith("AI_") and secondary.rule_id and not secondary.rule_id.startswith("AI_"):
            primary.rule_id = secondary.rule_id

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