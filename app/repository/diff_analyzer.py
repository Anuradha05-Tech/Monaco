# Why GitPython instead of shelling out to `git diff` manually:
# 1. Parsing raw diff stdout is error-prone and fragile (e.g., handling binary files,
#    renames, untracked/deleted files, and special character encodings).
# 2. GitPython provides structured access to the repository's git object database,
#    allowing us to inspect commits, trees, and diffs as Python objects.
# Limitations of GitPython:
# 1. It acts as a wrapper around the git command line interface, meaning it still
#    requires a git executable on the system and has some overhead.
# 2. Extracting exact added/modified line numbers is not natively structured in GitPython's
#    API; we still need to parse unified diff hunks (the patch text) to map changes to target line numbers.
# 3. Handling complex git scenarios like rename detection, binary file changes, merge commits,
#    and submodules requires carefully handling potential edge cases (which we document in our parser).
# 4. Known limitation with merge commits: Diffing against a merge commit target does not track
#    line-attribution from individual parent branches; it only shows the net logical changes
#    between the base commit and the merge commit.


import re
import logging
from pathlib import Path
import git

logger = logging.getLogger(__name__)

# Regex to match unified diff hunk header: @@ -old_start,old_len +new_start,new_len @@
# We extract Group 1 (new_start) and Group 2 (new_len, which is optional)
hunk_header_re = re.compile(r"^@@\s+-\d+(?:,\d+)?\s+\+(\d+)(?:,(\d+))?\s+@@")


class InvalidGitRefError(Exception):
    """Raised when a git reference (base or target) is invalid or does not exist."""
    pass


class DiffAnalyzer:
    """
    Analyzes git diffs to identify changed files and lines in a repository.
    """

    def __init__(self, repo_path: str):
        """
        Initializes the DiffAnalyzer.

        Args:
            repo_path: Path to the git repository.
        """
        self.repo_path = repo_path

    def get_changed_files(self, base: str = "HEAD~1", target: str = "HEAD") -> list[str]:
        """
        Returns a list of file paths (relative to repo root) that differ between the two refs.

        It includes added, modified, and renamed files, but excludes deleted files because
        they do not exist at the target reference.

        Args:
            base: The base git ref (default: "HEAD~1").
            target: The target git ref (default: "HEAD").

        Returns:
            A list of relative file paths.
        """
        repo = git.Repo(self.repo_path)
        try:
            commit_base = repo.commit(base)
        except Exception as e:
            raise InvalidGitRefError(f"Invalid git reference 'base': {base}") from e

        try:
            commit_target = repo.commit(target)
        except Exception as e:
            raise InvalidGitRefError(f"Invalid git reference 'target': {target}") from e

        diffs = commit_base.diff(commit_target)

        changed_files = []
        for diff in diffs:
            # Skip deleted files because we only return files that still exist at target
            if diff.change_type == 'D' or diff.deleted_file:
                continue
            if diff.b_path:
                changed_files.append(diff.b_path)

        return sorted(list(set(changed_files)))

    def get_changed_lines(self, file_path: str, base: str = "HEAD~1", target: str = "HEAD") -> list[int]:
        """
        Returns a list of line numbers in the file (as it exists at target) that were added or modified.

        Args:
            file_path: The file path relative to the repo root.
            base: The base git ref (default: "HEAD~1").
            target: The target git ref (default: "HEAD").

        Returns:
            A sorted list of line numbers (1-indexed) that were added or modified.
        """
        repo = git.Repo(self.repo_path)
        try:
            commit_base = repo.commit(base)
        except Exception as e:
            raise InvalidGitRefError(f"Invalid git reference 'base': {base}") from e

        try:
            commit_target = repo.commit(target)
        except Exception as e:
            raise InvalidGitRefError(f"Invalid git reference 'target': {target}") from e

        file_path_posix = Path(file_path).as_posix()

        # Compute diff restricted to the specific file and generate the patch text
        diffs = commit_base.diff(commit_target, paths=file_path_posix, create_patch=True)

        changed_lines = []

        for diff in diffs:
            if diff.b_path != file_path_posix:
                continue

            if diff.change_type == 'D' or diff.deleted_file:
                continue

            if not diff.diff:
                continue

            diff_text = diff.diff
            if isinstance(diff_text, bytes):
                diff_text = diff_text.decode("utf-8", errors="replace")

            current_target_line = None
            for line in diff_text.splitlines():
                match = hunk_header_re.match(line)
                if match:
                    current_target_line = int(match.group(1))
                    continue

                if current_target_line is not None:
                    # Ignore patch diff metadata lines that could start with +++/--- inside diff.diff
                    if line.startswith("+++") or line.startswith("---"):
                        continue
                    if line.startswith("+"):
                        changed_lines.append(current_target_line)
                        current_target_line += 1
                    elif line.startswith("-"):
                        # Deleted lines do not exist in target file
                        continue
                    elif line.startswith(" ") or not line:
                        current_target_line += 1

        return sorted(list(set(changed_lines)))
