from pathlib import Path

from app.scanner.file_types import LANGUAGE_EXTENSIONS


class RepositoryScanner:

    IGNORED_DIRECTORIES = {
        ".git",
        "node_modules",
        "venv",
        ".venv",
        "__pycache__",
        "dist",
        "build",
        ".idea",
        ".vscode"
    }

    def __init__(self, repository_path):
        self.repository_path = Path(repository_path)

    def scan(self):

        files = []

        for path in self.repository_path.rglob("*"):

            if not path.is_file():
                continue

            if any(
                directory in self.IGNORED_DIRECTORIES
                for directory in path.parts
            ):
                continue

            extension = path.suffix.lower()

            language = LANGUAGE_EXTENSIONS.get(
                extension,
                "Unknown"
            )

            files.append({
                "path": str(path),
                "extension": extension,
                "language": language
            })

        return files

    def read_file(self, file_path):

        path = Path(file_path)

        try:
            return path.read_text(
                encoding="utf-8"
            )

        except UnicodeDecodeError:
            return None


if __name__ == "__main__":

    scanner = RepositoryScanner(".")

    files = scanner.scan()

    print(f"Found {len(files)} files\n")

    for file in files:

        print(
            f"{file['path']} "
            f"→ {file['language']}"
        )

        if file["language"] == "Python":

            code = scanner.read_file(file["path"])

            if code:

                print("----- SOURCE CODE -----")
                print(code)
                print("-----------------------")