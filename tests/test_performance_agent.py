from app.agents.performance_agent import PerformanceAgent

def test_performance_agent_triggers():
    agent = PerformanceAgent()
    
    code_trigger = """
def concat_in_loop():
    s = ""
    for i in range(10):
        s += "a"  # PERF001

def sum_list_comp():
    # PERF002
    x = sum([i for i in range(5)])
    y = any([False, True])
"""
    findings = agent.analyze("test.py", code_trigger)
    rule_ids = {f.rule_id for f in findings}
    
    assert "PERF001" in rule_ids
    assert "PERF002" in rule_ids

def test_performance_agent_non_triggers():
    agent = PerformanceAgent()
    
    code_non_trigger = """
def good_concat():
    parts = []
    for i in range(10):
        parts.append("a")
    s = "".join(parts)

def generator_expr():
    x = sum(i for i in range(5))
    y = any(x for x in [False, True])

def integer_addition_in_loop():
    count = 0
    for i in range(10):
        count += 1 # Not string concatenation!
"""
    findings = agent.analyze("test.py", code_non_trigger)
    assert len(findings) == 0
