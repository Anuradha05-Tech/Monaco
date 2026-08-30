from app.github.github_client import GitHubClient
from app.github.pr_diff_parser import PRDiffParser
from app.repository.dependency_graph import DependencyGraphBuilder
from app.repository.context_retriever import ContextRetriever

class PRContextBuilder:
    """
    Builds a unified code review context from a GitHub Pull Request and a local workspace.
    
    This class integrates GitHub PR metadata and file diffs with a local dependency graph,
    allowing the downstream AI code review layer to understand what changed and what code
    is contextually related to the changes.
    
    Convergence Note:
        The dictionary format returned by this builder mirrors the output format of Phase 10's
        `DiffContextBuilder`. In a future phase, these two paths (local git diff context and GitHub PR
        diff context) will be converged into a unified context representation for the AI review layer.
    """
    def __init__(
        self,
        github_client: GitHubClient,
        pr_diff_parser: PRDiffParser,
        graph_builder: DependencyGraphBuilder,
        context_retriever_class=ContextRetriever
    ):
        """
        Initializes the PRContextBuilder.
        
        Args:
            github_client: An instance of GitHubClient.
            pr_diff_parser: An instance of PRDiffParser.
            graph_builder: An instance of DependencyGraphBuilder (or a pre-built dict mapping file paths to imports).
            context_retriever_class: The ContextRetriever class to instantiate for dependency analysis.
        """
        self.github_client = github_client
        self.pr_diff_parser = pr_diff_parser
        self.graph_builder = graph_builder
        self.context_retriever_class = context_retriever_class

    def build_pr_review_context(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        local_repo_path: str
    ) -> dict:
        """
        Fetches PR details from GitHub and maps changes to the local repository's dependency graph.
        
        Assumption & Limitation:
            This method assumes that the repository cloned at `local_repo_path` is checked out
            to the PR's exact head branch. 
            
            No validation is performed to check whether `local_repo_path` matches the PR's actual
            head branch. If the paths do not match or are pointed at an unrelated repository:
              1. Files modified/added on GitHub might not exist in the local workspace, and won't be
                 found in the dependency graph.
              2. The retrieved context (related files) could be incomplete or incorrect due to dependency
                 mismatches between the local graph and the PR head state.
        
        Args:
            owner: The GitHub repository owner.
            repo: The GitHub repository name.
            pr_number: The pull request number.
            local_repo_path: The absolute local path to the repository clone.
            
        Returns:
            A dictionary containing:
                "pr_title": The title of the pull request.
                "pr_number": The pull request number.
                "changed_files": A list of relative paths of changed files.
                "changed_lines": A dict mapping file path strings to lists of added line numbers.
                "related_files": A dict mapping file path strings to lists of related file paths.
        """
        # 1. Fetch Pull Request metadata and changed files list from GitHub
        pr_meta = self.github_client.get_pull_request(owner, repo, pr_number)
        pr_title = pr_meta.get("title", "")
        
        pr_files = self.github_client.get_pr_files(owner, repo, pr_number)
        
        changed_files = []
        changed_lines = {}
        
        # 2. Parse the patch for each file to get added line numbers
        for file_entry in pr_files:
            filename = file_entry.get("filename")
            if not filename:
                continue
            
            patch_text = file_entry.get("patch")
            added_lines = self.pr_diff_parser.parse_patch(patch_text)
            
            changed_files.append(filename)
            changed_lines[filename] = added_lines
            
        # 3. Build/Retrieve the dependency graph of the local repo
        if hasattr(self.graph_builder, "build"):
            graph = self.graph_builder.build(local_repo_path)
        else:
            # Fallback to pre-built dictionary if passed directly
            graph = self.graph_builder
            
        retriever = self.context_retriever_class(graph)
        
        # 4. Map each changed file to contextually related files in the graph (depth=1)
        related_files = {}
        for filename in changed_files:
            related = retriever.get_related_files(filename, depth=1)
            related_files[filename] = related
            
        return {
            "pr_title": pr_title,
            "pr_number": pr_number,
            "changed_files": changed_files,
            "changed_lines": changed_lines,
            "related_files": related_files
        }
