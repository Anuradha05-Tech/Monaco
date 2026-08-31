from app.agents.quality_agent import QualityAgent

def test_quality_agent_checks():
    agent = QualityAgent()
    
    # 1. Triggers
    code_trigger = """
def long_function():
    # Let's make it more than 50 lines
    a = 1
    a = 2
    a = 3
    a = 4
    a = 5
    a = 6
    a = 7
    a = 8
    a = 9
    a = 10
    a = 11
    a = 12
    a = 13
    a = 14
    a = 15
    a = 16
    a = 17
    a = 18
    a = 19
    a = 20
    a = 21
    a = 22
    a = 23
    a = 24
    a = 25
    a = 26
    a = 27
    a = 28
    a = 29
    a = 30
    a = 31
    a = 32
    a = 33
    a = 34
    a = 35
    a = 36
    a = 37
    a = 38
    a = 39
    a = 40
    a = 41
    a = 42
    a = 43
    a = 44
    a = 45
    a = 46
    a = 47
    a = 48
    a = 49
    a = 50
    a = 51

def nested_function():
    if True: # 1
        for i in range(1): # 2
            while False: # 3
                try: # 4
                    if True: # 5
                        pass
                except Exception:
                    pass

def no_docstring_long():
    a = 1
    a = 2
    a = 3
    a = 4
    a = 5
    a = 6

def bare_except():
    try:
        x = 1
    except:
        pass
"""
    findings = agent.analyze("test.py", code_trigger)
    rule_ids = {f.rule_id for f in findings}
    
    assert "QUAL001" in rule_ids
    assert "QUAL002" in rule_ids
    assert "QUAL003" in rule_ids
    assert "QUAL004" in rule_ids

def test_quality_agent_non_triggers():
    agent = QualityAgent()
    
    code_non_trigger = """
def short_func():
    \"\"\"This is a short function with docstring.\"\"\"
    return 42

def nested_shallow():
    if True:
        if False:
            pass

def short_no_doc():
    pass # Under 5 lines, so no docstring is fine

def spec_except():
    try:
        x = 1
    except ValueError:
        pass
"""
    findings = agent.analyze("test.py", code_non_trigger)
    assert len(findings) == 0
