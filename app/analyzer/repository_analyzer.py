from app.scanner.repository_scanner import RepositoryScanner
from app.analyzer.python_analyzer import PythonAnalyzer


class RepositoryAnalyzer:

    def __init__(self, repository_path):

        self.scanner = RepositoryScanner(repository_path)
        self.python_analyzer = PythonAnalyzer()

    def analyze(self):

        files = self.scanner.scan()

        results = []

        for file in files:

            if file["language"] != "Python":
                continue

            code = self.scanner.read_file(file["path"])

            if code is None:
                continue

            try:

                analysis = self.python_analyzer.analyze(code)

                results.append({
                    "file": file["path"],
                    "language": file["language"],
                    "analysis": analysis
                })

            except SyntaxError as error:

                results.append({
                    "file": file["path"],
                    "language": file["language"],
                    "error": str(error)
                })

        return results


if __name__ == "__main__":

    analyzer = RepositoryAnalyzer(".")

    results = analyzer.analyze()

    for result in results:

        print("\n==============================")
        print("FILE:", result["file"])
        print("==============================")

        if "error" in result:

            print("Syntax Error:", result["error"])

        else:

            print("Language:", result["language"])

            print(
                "Functions:",
                result["analysis"]["functions"]
            )

            print(
                "Classes:",
                result["analysis"]["classes"]
            )

            print(
                "Imports:",
                result["analysis"]["imports"]
            )