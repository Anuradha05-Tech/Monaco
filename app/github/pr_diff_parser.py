import re

# Regex to match the hunk header format: @@ -old_start,old_count +new_start,new_count @@
HUNK_HEADER_RE = re.compile(r'^@@\s+-\d+(?:,\d+)?\s+\+(\d+)(?:,(\d+))?\s+@@')

class PRDiffParser:
    """
    Parses unified diff patch text from the GitHub REST API to extract added line numbers.
    """
    def parse_patch(self, patch_text: str | None) -> list[int]:
        """
        Parses patch text and returns a list of line numbers added in the new version of the file.
        
        Args:
            patch_text: Unified diff patch content from GitHub.
            
        Returns:
            A list of 1-indexed line numbers that were added.
        """
        if not patch_text:
            return []
        
        added_lines = []
        current_line = 0
        
        for line in patch_text.splitlines():
            match = HUNK_HEADER_RE.match(line)
            if match:
                # We found a new hunk header!
                # The start line of the new file is in capture group 1.
                current_line = int(match.group(1))
                continue
            
            # If we haven't encountered a hunk header yet, skip lines
            if current_line == 0:
                continue
            
            if line.startswith("+"):
                # Exclude the "+++" header line if it happens to be in the patch
                if line.startswith("+++"):
                    continue
                added_lines.append(current_line)
                current_line += 1
            elif line.startswith("-"):
                # Deletions do not affect the line numbers of the new file
                continue
            elif line.startswith(" "):
                # Context line is present in the new file
                current_line += 1
            elif line.startswith("\\"):
                # No newline at end of file, or other unified diff metadata
                continue
            elif not line:
                # Fallback for an empty line (treated as context)
                current_line += 1
            else:
                # Fallback for other lines (treated as context)
                current_line += 1
                
        return added_lines
