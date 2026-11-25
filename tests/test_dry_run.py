from ps5watch.dry_run import run_dry


def test_dry_run_prints_max_alert_then_repeat():
    sent = run_dry()
    assert len(sent) == 2
    assert "ALERTA MÁXIMO" in sent[0]
    assert "R$ 3.500,00" in sent[0]
    assert "ALERTA MÁXIMO" in sent[1]
