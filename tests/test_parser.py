"""Tests for mmcalc.parser."""

from mmcalc.parser import parse_calculation, parse_file


def test_parse_step_with_justification():
    step_text = "X_ x e. A B =/= (/) { by (n0) using (bicomi) }"
    calc = parse_calculation(step_text)
    assert len(calc.steps) == 1
    step = calc.steps[0]
    assert step.expression == "X_ x e. A B =/= (/)"
    assert step.justification is not None
    assert "n0" in step.justification.rule_refs
    assert "bicomi" in step.justification.using_refs


def test_parse_step_with_indexed_rule():
    step_text = "A. x e. A B =/= (/) { by (ac6s4) and (Ac9.1) } (-1:impbii)"
    calc = parse_calculation(step_text)
    assert len(calc.steps) == 1
    step = calc.steps[0]
    assert step.expression == "A. x e. A B =/= (/)"
    assert step.justification is not None
    assert [r for r in step.justification.join_refs] == [(-1, "impbii")]
    assert "impbii" not in step.justification.rule_refs
    assert "ac6s4" in step.justification.rule_refs


def test_parse_step_with_join_ref():
    step_text = "X_ x e. A B =/= (/) { by (n0) using (bicomi) } (bitri)"
    calc = parse_calculation(step_text)
    assert len(calc.steps) == 1
    step = calc.steps[0]
    assert step.expression == "X_ x e. A B =/= (/)"
    assert step.justification is not None
    assert step.justification.rule_refs == ["n0"]
    assert step.justification.using_refs == ["bicomi"]
    assert step.justification.join_refs == [(None, "bitri")]


def test_parse_step_join_ref_relational_expression():
    step_text = "<-> { by (r1) } (bitri)"
    calc = parse_calculation(step_text)
    assert len(calc.steps) == 1
    step = calc.steps[0]
    assert step.expression == "<->"
    assert step.justification is not None
    assert step.justification.rule_refs == ["r1"]
    assert step.justification.join_refs == [(None, "bitri")]


def test_parse_calculation_multiple_steps():
    text = "A = B { by (bitri) }\nB = C { by (eqtrd) }"
    calc = parse_calculation(text)
    assert len(calc.steps) == 2


def test_parse_file_simple():
    text = (
        "$[ set.mm $]\n"
        "${\n"
        "$d f x A $.  $d f B $.\n"
        "myac9.1 $e |- A e. _V $.\n"
        "myac9s $p |- ( A. x e. A B =/= (/) <-> X_ x e. A B =/= (/) ) $=\n"
        "  cB c0 wne vx cA wral impbii $.\n"
        "$}\n"
        "X_ x e. A B =/= (/)\n"
        "    <-> { by (n0) using (bicomi) } (bitri)\n"
        "    E. f f e. X_ x e. A B\n"
        "    ."
    )
    pf = parse_file(text)
    assert pf.theorem_label == "myac9s"
    assert pf.hypotheses == [("myac9.1", "|- A e. _V")]
    assert pf.disjoint == ["f x A", "f B"]
    assert pf.proof_tokens == "cB c0 wne vx cA wral impbii"
    assert len(pf.calculations) >= 1


def test_parse_file_multi_step():
    text = (
        "* (Ac9.1) |- A e. _V $==>\n"
        "    A = B { by (bitri) }\n"
        "    B = C { by (eqtrd) }\n"
        "    .\n"
        "    C = D { by (eqtrd) }\n"
        "    ."
    )
    pf = parse_file(text)
    assert len(pf.calculations) == 2
    assert len(pf.calculations[0].steps) == 2
    assert len(pf.calculations[1].steps) == 1


def test_parse_relation_operators():
    text = "A <-> B { by (bitri) }"
    calc = parse_calculation(text)
    assert len(calc.steps) == 1
    assert calc.steps[0].expression == "A <-> B"
