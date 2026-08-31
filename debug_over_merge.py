import os
import sys

# Ensure project root is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.engine.review_engine import ReviewEngine
from app.engine.deduplicator import FindingDeduplicator
from app.models.finding import Finding

def main():
    print("=== Diagnostic: Finding Over-Merge Debugger ===")
    
    # We will simulate the raw findings generated from reviewing app.py.
    # From app.py, we have two hardcoded secrets:
    # Line 7: API_KEY = "sk-hardcoded-secret-12345"
    # Line 8: SECRET_TOKEN = 'sk-another-test-secret-999'
    
    # Let's run ReviewEngine's internal steps to see where the merge happens.
    engine = ReviewEngine()
    
    # Read app.py content
    app_py_path = "/home/user/Documents/monaco-test-repo-clone/app.py"
    with open(app_py_path, "r") as f:
        code = f.read()
        
    print("\n--- Step 1: Running analyzer and LLM to collect raw findings ---")
    static_result = engine.analyzer.analyze(code)
    static_findings = static_result["findings"]
    print(f"Static analyzer returned {len(static_findings)} findings:")
    for f in static_findings:
        print(f"  - Rule: {f.rule_id} | Line: {f.line} | Msg: {repr(f.message)}")
        
    data_flow_findings = engine.data_flow_analyzer.analyze(code)
    print(f"Data-flow analyzer returned {len(data_flow_findings)} findings.")
    
    ai_review = engine.llm.review_code(code)
    ai_findings = ai_review.findings
    print(f"AI reviewer returned {len(ai_findings)} findings:")
    for f in ai_findings:
        print(f"  - Rule: {f.rule_id} | Line: {f.line} | Msg: {repr(f.message)}")
        
    all_findings = []
    all_findings.extend(static_findings)
    all_findings.extend(data_flow_findings)
    all_findings.extend(ai_findings)
    
    print(f"\nTotal raw findings before deduplication: {len(all_findings)}")
    for idx, f in enumerate(all_findings, 1):
        print(f"Raw #{idx}: Rule={f.rule_id}, Category={f.category}, Line={f.line}, Msg={repr(f.message)}")
        
    # Now let's trace are_duplicates between the two SEC002 findings
    print("\n--- Step 2: Tracing are_duplicates check between the two SEC002 findings ---")
    # Finding 1: SEC002 on line 7
    f1 = [f for f in static_findings if f.rule_id == "SEC002" and f.line == 7][0]
    # Finding 2: SEC002 on line 8 (or whichever line was returned by the analyzer/AI)
    f2_candidates = [f for f in static_findings if f.rule_id == "SEC002" and f.line != 7]
    if f2_candidates:
        f2 = f2_candidates[0]
        
        # Let's inspect the results of each check in are_duplicates
        cat_match = (f1.category == f2.category)
        rule_compat = engine.deduplicator.are_rule_ids_compatible(f1.rule_id, f2.rule_id)
        line_dist = abs(f1.line - f2.line) if (f1.line is not None and f2.line is not None) else None
        line_compat = (line_dist <= engine.deduplicator.LINE_DISTANCE) if line_dist is not None else True
        both_structured = (f1.rule_id is not None and f2.rule_id is not None)
        
        print(f"Comparing:")
        print(f"  Finding A: Rule={f1.rule_id}, Line={f1.line}, Msg={repr(f1.message)}")
        print(f"  Finding B: Rule={f2.rule_id}, Line={f2.line}, Msg={repr(f2.message)}")
        print(f"  1. Category Match:        {cat_match} (A: {repr(f1.category)}, B: {repr(f2.category)})")
        print(f"  2. Rule ID Compatibility: {rule_compat} (A: {repr(f1.rule_id)}, B: {repr(f2.rule_id)})")
        print(f"  3. Line Distance:         {line_dist} (LINE_DISTANCE limit: {engine.deduplicator.LINE_DISTANCE})")
        print(f"  4. Both Structured rule_id? {both_structured}")
        
        is_dup = engine.deduplicator.are_duplicates(f1, f2)
        print(f"  => are_duplicates() result: {is_dup}")
    else:
        print("No second SEC002 static finding found.")
        
    print("\n--- Step 3: Running ReviewEngine.review() ---")
    final_findings = engine.review(code)
    print(f"ReviewEngine.review() returned {len(final_findings)} findings:")
    for f in final_findings:
        print(f"  - Rule: {f.rule_id} | Line: {f.line} | Msg: {repr(f.message)}")
        
if __name__ == "__main__":
    main()
