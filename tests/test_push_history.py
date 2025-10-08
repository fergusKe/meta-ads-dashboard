from importlib import reload


def test_push_history_record(tmp_path, monkeypatch):
    path = tmp_path / "history.parquet"
    monkeypatch.setenv("PUSH_HISTORY_PATH", str(path))

    from utils import push_history

    reload(push_history)

    push_history.record("C1", "A", "fatigue_push", "Slack", "sent", "replace asset")
    push_history.record("C1", "B", "fatigue_push", "Slack", "pending", "await approval")
    push_history.record("C2", "C", "fatigue_push", "Email", "sent", "notify CS")

    recent = push_history.load_history()
    assert len(recent) == 3
    assert set(recent["status"]) == {"sent", "pending"}

    summary = push_history.summarize_by_campaign()
    assert list(summary.columns) == ["campaign_id", "pushes", "success", "pending"]
    row = summary[summary["campaign_id"] == "C1"].iloc[0]
    assert int(row["pushes"]) == 2
    assert int(row["success"]) == 1
