from app.repository.dependency_graph import DependencyGraphBuilder
from app.repository.diff_analyzer import DiffAnalyzer
from app.repository.context_retriever import ContextRetriever


class DiffContextBuilder:
    """
    Combines git diff information and repository dependency structures to build a complete review context.

    This context is the core input format intended for the downstream AI code review layer,
    allowing the AI model to understand the exact modified line ranges along with their import
    and dependency relationships in the wider codebase.
    """

    def __init__(self, graph_builder: DependencyGraphBuilder, diff_analyzer: DiffAnalyzer):
        """
        Initializes the DiffContextBuilder.

        Args:
            graph_builder: An instance of DependencyGraphBuilder.
            diff_analyzer: An instance of DiffAnalyzer.
        """
        self.graph_builder = graph_builder
        self.diff_analyzer = diff_analyzer

    def build_review_context(self, base: str = "HEAD~1", target: str = "HEAD") -> dict:
        """
        Builds the unified code review context between two git references.

        Args:
            base: The base git ref (default: "HEAD~1").
            target: The target git ref (default: "HEAD").

        Returns:
            A dictionary containing:
                "changed_files": A list of relative paths of changed files.
                "changed_lines": A dict mapping file path strings to lists of changed line numbers.
                "related_files": A dict mapping file path strings to lists of related file paths (depth=1).
        """
        changed_files = self.diff_analyzer.get_changed_files(base, target)

        changed_lines = {}
        for file in changed_files:
            lines = self.diff_analyzer.get_changed_lines(file, base, target)
            changed_lines[file] = lines

        repo_root = self.diff_analyzer.repo_path
        graph = self.graph_builder.build(repo_root)
        retriever = ContextRetriever(graph)

        related_files = {}
        for file in changed_files:
            related = retriever.get_related_files(file, depth=1)
            related_files[file] = related

        return {
            "changed_files": changed_files,
            "changed_lines": changed_lines,
            "related_files": related_files
        }
