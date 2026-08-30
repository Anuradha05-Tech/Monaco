import os
import sys

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.analyzer.python_analyzer import PythonAnalyzer
from app.analyzer.data_flow_analyzer import DataFlowAnalyzer
from app.ai.llm_client import LLMClient
from app.engine.deduplicator import FindingDeduplicator
from app.engine.validator import FindingValidator, ValidationResult
from app.engine.ranker import FindingRanker

def main():
    code = """import subprocess

def run_backup(filename):
    # BUG: shell=True + unsanitized input = command injection
    subprocess.run(f"tar -cvf backup.tar {filename}", shell=True)

API_KEY = "sk-hardcoded-secret-12345"  # BUG: hardcoded secret
"""

    print("--- Stage 0: Run All Analyzers ---")
    
    # 1. PythonAnalyzer
    analyzer = PythonAnalyzer()
    static_findings = analyzer.analyze(code)["findings"]
    print(f"Static findings count: {len(static_findings)}")
    for f in static_findings:
        print(f"  [Static] Rule: {f.rule_id} | Line: {f.line} | Message: {f.message} | Source: {f.source}")
        
    # 2. DataFlowAnalyzer
    df_analyzer = DataFlowAnalyzer()
    df_findings = df_analyzer.analyze(code)
    print(f"DataFlow findings count: {len(df_findings)}")
    for f in df_findings:
        print(f"  [DataFlow] Rule: {f.rule_id} | Line: {f.line} | Message: {f.message} | Source: {f.source}")
        
    # 3. LLMClient
    llm = LLMClient()
    ai_review = llm.review_code(code)
    ai_findings = ai_review.findings
    print(f"AI findings count: {len(ai_findings)}")
    for f in ai_findings:
        print(f"  [AI] Rule: {f.rule_id} | Line: {f.line} | Message: {f.message} | Source: {f.source}")

    # Combine all findings
    all_findings = []
    all_findings.extend(static_findings)
    all_findings.extend(df_findings)
    all_findings.extend(ai_findings)
    print(f"\nTotal Combined findings: {len(all_findings)}")
    for f in all_findings:
         print(f"  Rule: {f.rule_id} | Line: {f.line} | Message: {f.message} | Source: {f.source}")

    print("\n--- Stage 1: FindingDeduplicator ---")
    dedup = FindingDeduplicator()
    deduped = dedup.deduplicate(all_findings)
    print(f"Count after dedup: {len(deduped)}")
    for f in deduped:
        print(f"  Rule: {f.rule_id} | Line: {f.line} | Message: {f.message} | Sources: {f.sources if f.sources else [f.source]}")

    print("\n--- Stage 2: FindingValidator ---")
    validator = FindingValidator()
    validated = []
    for f in deduped:
        val_res = validator.validate(code, f)
        print(f"  Rule: {f.rule_id} | Message: {f.message} | Validation: {val_res}")
        if val_res == ValidationResult.VALID:
            validated.append(f)
    print(f"Count after validation: {len(validated)}")
    for f in validated:
        print(f"  Rule: {f.rule_id} | Line: {f.line} | Message: {f.message} | Sources: {f.sources}")

    print("\n--- Stage 3: FindingRanker ---")
    ranker = FindingRanker()
    ranked = ranker.rank(validated)
    print(f"Count after ranking: {len(ranked)}")
    for f in ranked:
        print(f"  Rule: {f.rule_id} | Line: {f.line} | Message: {f.message} | Sources: {f.sources}")

if __name__ == "__main__":
    main()
