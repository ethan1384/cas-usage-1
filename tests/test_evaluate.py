from lumio.evaluate import metrics, render_report


def test_metrics_separate_costly_errors_from_safe_ones():
    pairs = [
        ("qualifie", "qualifie"),
        ("qualifie", "a_revoir"),  # prudent : un humain regarde
        ("qualifie", "hors_cible"),  # lead perdu
        ("hors_cible", "hors_cible"),
        ("hors_cible", "qualifie"),  # faux qualifié
        ("a_revoir", "a_revoir"),
    ]
    result = metrics(pairs)
    assert result["lost_leads"] == 1
    assert result["false_qualified"] == 1
    assert (result["filtered"], result["expected_out"]) == (1, 2)
    assert (result["auto_qualified"], result["expected_qualified"]) == (1, 3)
    assert result["accuracy"] == 3 / 6
    assert result["review_share"] == 2 / 6
    assert result["matrix"]["qualifie"]["hors_cible"] == 1


def test_report_lists_only_disagreements():
    rows = [
        {"id": "ok", "category": "c", "expected": "qualifie", "rules": "qualifie", "full": "qualifie", "reason": "x"},
        {"id": "ko", "category": "c", "expected": "hors_cible", "rules": "qualifie", "full": "a_revoir", "reason": "y"},
    ]
    report = render_report(rows, "modele-test")
    assert "| ko |" in report
    assert "| ok |" not in report
