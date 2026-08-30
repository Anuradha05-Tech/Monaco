from app.models.finding import Finding

class ReviewCommentFormatter:
    """
    Formats Monaco review findings into markdown review comments for GitHub PRs.
    """

    def format_finding(self, finding: Finding) -> str:
        """
        Formats a single Finding object into a professional, user-friendly markdown body.
        """
        # Map raw source identifiers to friendly names
        sources = finding.sources if finding.sources else [finding.source]
        friendly_sources = []
        for s in sources:
            if s == "static_analyzer":
                friendly_sources.append("static analysis")
            elif s == "data_flow":
                friendly_sources.append("data-flow tracing")
            elif s == "ai":
                friendly_sources.append("AI review")
            else:
                friendly_sources.append(s)
        
        detected_by = " + ".join(friendly_sources)

        # Generate markdown template
        markdown = (
            f"### ⚠️ MONACO Code Review Finding\n\n"
            f"- **Category:** {finding.category}\n"
            f"- **Severity:** {finding.severity.value if hasattr(finding.severity, 'value') else finding.severity}\n"
            f"- **Message:** {finding.message}\n\n"
            f"#### Explanation\n"
            f"{finding.explanation or 'No detailed explanation provided.'}\n\n"
            f"#### Suggestion\n"
            f"{finding.suggestion or 'No specific suggestion provided.'}\n\n"
            f"---  \n"
            f"*Detected by: {detected_by}*"
        )
        return markdown

    def build_review_comments(self, findings: list[Finding]) -> list[dict]:
        """
        Filters list of findings to only those in the PR diff, and maps them to GitHub review comments.
        """
        comments = []
        for f in findings:
            if not f.in_diff:
                continue
            
            comments.append({
                "path": f.file,
                "line": f.line,
                "body": self.format_finding(f),
                # "side": "RIGHT" is explicitly set here because we want to comment on the new code 
                # changes (the right side of the diff/PR head commit).
                "side": "RIGHT"
            })
        return comments
