import os
from app.graph.state import ReviewState
from app.engine.review_engine import ReviewEngine
from app.github.pr_context_builder import PRContextBuilder
from app.engine.validator import ValidationResult

from app.agents.security_agent import SecurityAgent
from app.agents.quality_agent import QualityAgent
from app.agents.performance_agent import PerformanceAgent

class ReviewGraphNodes:
    """
    Implements the nodes for the PR review LangGraph.
    """
    def __init__(self, pr_context_builder: PRContextBuilder, review_engine: ReviewEngine):
        self.pr_context_builder = pr_context_builder
        self.review_engine = review_engine
        
        # Instantiate the new specialized agents
        self.security_agent = SecurityAgent(review_engine)
        self.quality_agent = QualityAgent()
        self.performance_agent = PerformanceAgent()

    def fetch_pr_context_node(self, state: ReviewState) -> dict:
        """
        Retrieves the PR context from GitHub and local repository structure.
        """
        context = self.pr_context_builder.build_pr_review_context(
            owner=state["owner"],
            repo=state["repo"],
            pr_number=state["pr_number"],
            local_repo_path=state["local_repo_path"]
        )

        return {
            "pr_context": context,
            "status_logs": ["fetch_pr_context_node"]
        }

    def security_agent_node(self, state: ReviewState) -> dict:
        """
        Runs the security review agent on all changed Python files.
        """
        pr_context = state["pr_context"] or {}
        changed_files = pr_context.get("changed_files", [])
        changed_lines = pr_context.get("changed_lines", {})
        local_repo_path = state["local_repo_path"]

        skipped = []
        findings = []

        for filename in changed_files:
            file_path = os.path.join(local_repo_path, filename)
            if not os.path.exists(file_path) or os.path.isdir(file_path):
                skipped.append(filename)
                continue
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    code = f.read()
            except Exception:
                skipped.append(filename)
                continue

            agent_findings = self.security_agent.analyze(filename, code)
            lines_changed = changed_lines.get(filename, [])
            for finding in agent_findings:
                finding.in_diff = (finding.line is not None and finding.line in lines_changed)
                findings.append(finding)

        return {
            "security_findings": findings,
            "skipped_files": skipped,
            "status_logs": ["security_agent_node"]
        }

    def quality_agent_node(self, state: ReviewState) -> dict:
        """
        Runs the AST-based code quality agent on all changed Python files.
        """
        pr_context = state["pr_context"] or {}
        changed_files = pr_context.get("changed_files", [])
        changed_lines = pr_context.get("changed_lines", {})
        local_repo_path = state["local_repo_path"]

        skipped = []
        findings = []

        for filename in changed_files:
            file_path = os.path.join(local_repo_path, filename)
            if not os.path.exists(file_path) or os.path.isdir(file_path):
                skipped.append(filename)
                continue
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    code = f.read()
            except Exception:
                skipped.append(filename)
                continue

            agent_findings = self.quality_agent.analyze(filename, code)
            lines_changed = changed_lines.get(filename, [])
            for finding in agent_findings:
                finding.in_diff = (finding.line is not None and finding.line in lines_changed)
                findings.append(finding)

        return {
            "quality_findings": findings,
            "skipped_files": skipped,
            "status_logs": ["quality_agent_node"]
        }

    def performance_agent_node(self, state: ReviewState) -> dict:
        """
        Runs the AST-based performance agent on all changed Python files.
        """
        pr_context = state["pr_context"] or {}
        changed_files = pr_context.get("changed_files", [])
        changed_lines = pr_context.get("changed_lines", {})
        local_repo_path = state["local_repo_path"]

        skipped = []
        findings = []

        for filename in changed_files:
            file_path = os.path.join(local_repo_path, filename)
            if not os.path.exists(file_path) or os.path.isdir(file_path):
                skipped.append(filename)
                continue
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    code = f.read()
            except Exception:
                skipped.append(filename)
                continue

            agent_findings = self.performance_agent.analyze(filename, code)
            lines_changed = changed_lines.get(filename, [])
            for finding in agent_findings:
                finding.in_diff = (finding.line is not None and finding.line in lines_changed)
                findings.append(finding)

        return {
            "performance_findings": findings,
            "skipped_files": skipped,
            "status_logs": ["performance_agent_node"]
        }

    def merge_agent_findings_node(self, state: ReviewState) -> dict:
        """
        Merges findings from the security, quality, and performance agents into all_findings.
        """
        security = state.get("security_findings") or []
        quality = state.get("quality_findings") or []
        performance = state.get("performance_findings") or []

        combined = []
        combined.extend(security)
        combined.extend(quality)
        combined.extend(performance)

        return {
            "all_findings": combined,
            "status_logs": ["merge_agent_findings_node"]
        }

    def deduplicate_node(self, state: ReviewState) -> dict:
        """
        Deduplicates and merges proximate/redundant findings.
        """
        all_findings = state.get("all_findings", [])
        deduped = self.review_engine.deduplicator.deduplicate(all_findings)

        return {
            "deduplicated_findings": deduped,
            "status_logs": ["deduplicate_node"]
        }

    def validate_node(self, state: ReviewState) -> dict:
        """
        Validates findings against the source code syntax tree and records the rejection ratio.
        """
        deduped = state.get("deduplicated_findings", [])
        local_repo_path = state["local_repo_path"]

        validated_findings = []
        checked_count = 0
        rejected_count = 0

        # Cache file content reads to avoid re-reading the same file repeatedly
        file_cache = {}

        for finding in deduped:
            checked_count += 1
            filename = finding.file
            if not filename:
                rejected_count += 1
                continue

            if filename not in file_cache:
                file_path = os.path.join(local_repo_path, filename)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        file_cache[filename] = f.read()
                except Exception:
                    file_cache[filename] = None

            code = file_cache[filename]
            if code is None:
                rejected_count += 1
                continue

            validation_result = self.review_engine.validator.validate(code, finding)
            if validation_result == ValidationResult.VALID:
                validated_findings.append(finding)
            else:
                rejected_count += 1

        rejection_ratio = rejected_count / checked_count if checked_count > 0 else 0.0

        return {
            "validated_findings": validated_findings,
            "rejection_ratio": rejection_ratio,
            "status_logs": ["validate_node"]
        }

    def rank_node(self, state: ReviewState) -> dict:
        """
        Ranks validated findings by severity and confidence.
        """
        validated = state.get("validated_findings", [])
        # If validated is not set yet, fallback to deduplicated_findings to be robust
        if not validated and not state.get("rejection_ratio"):
            validated = state.get("deduplicated_findings", [])

        ranked = self.review_engine.ranker.rank(validated)

        return {
            "final_findings": ranked,
            "status_logs": ["rank_node"]
        }

    def flag_for_manual_review_node(self, state: ReviewState) -> dict:
        """
        Flags the review for manual human override due to high AI/heuristic disagreement.
        """
        ratio = state.get('rejection_ratio', 0.0)
        return {
            "needs_manual_review": True,
            "status_logs": ["flag_for_manual_review_node", f"Flagged: High rejection ratio ({ratio:.2%})"]
        }
