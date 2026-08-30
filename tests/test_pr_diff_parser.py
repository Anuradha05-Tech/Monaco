from app.github.pr_diff_parser import PRDiffParser

def test_parse_patch_single_hunk():
    parser = PRDiffParser()
    patch = (
        "@@ -1,3 +1,4 @@\n"
        " line1\n"
        "+line2\n"
        " line3\n"
        " line4"
    )
    # Line 1 is context (line 1 in new file)
    # Line 2 is added (+line2) -> line 2 in new file
    # Line 3 is context -> line 3 in new file
    # Line 4 is context -> line 4 in new file
    # Added lines: [2]
    added = parser.parse_patch(patch)
    assert added == [2]

def test_parse_patch_multiple_hunks():
    parser = PRDiffParser()
    patch = (
        "@@ -5,4 +5,5 @@\n"
        " line5\n"
        "+line6\n"
        " line7\n"
        " line8\n"
        "@@ -20,3 +21,5 @@\n"
        " line21\n"
        "+line22\n"
        "+line23\n"
        " line24"
    )
    # Hunk 1 starting at 5:
    # 5: context (line 5) -> current_line increments to 6
    # 6: added (+line6) -> added lines gets 6, current_line increments to 7
    # 7: context (line 7) -> current_line increments to 8
    # 8: context (line 8) -> current_line increments to 9
    
    # Hunk 2 starting at 21:
    # 21: context (line 21) -> current_line increments to 22
    # 22: added (+line22) -> added lines gets 22, current_line increments to 23
    # 23: added (+line23) -> added lines gets 23, current_line increments to 24
    # 24: context (line 24) -> current_line increments to 25
    
    added = parser.parse_patch(patch)
    assert added == [6, 22, 23]

def test_parse_patch_none_or_empty():
    parser = PRDiffParser()
    assert parser.parse_patch(None) == []
    assert parser.parse_patch("") == []

def test_parse_patch_only_deletions():
    parser = PRDiffParser()
    patch = (
        "@@ -10,3 +10,1 @@\n"
        " line10\n"
        "-line11\n"
        "-line12\n"
        " line13"
    )
    # 10: context (line 10) -> current_line increments to 11
    # -line11: deletion -> ignored
    # -line12: deletion -> ignored
    # 11: context (line 13) -> current_line increments to 12
    # Added lines should be empty
    added = parser.parse_patch(patch)
    assert added == []

def test_parse_patch_with_no_newline_indicator():
    parser = PRDiffParser()
    patch = (
        "@@ -1,2 +1,3 @@\n"
        " line1\n"
        "+line2\n"
        "\\ No newline at end of file"
    )
    added = parser.parse_patch(patch)
    assert added == [2]
