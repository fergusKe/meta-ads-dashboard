from importlib import reload


def test_usage_store_flow(tmp_path, monkeypatch):
    path = tmp_path / "events.parquet"
    monkeypatch.setenv("FEATURE_USAGE_EVENT_PATH", str(path))

    from utils import usage_store

    reload(usage_store)

    usage_store.record_event("roi_simulator", "simulate", {"scenario": "A"})
    usage_store.record_event("roi_simulator", "download_ppt", {"scenario": "A"})
    usage_store.record_event("roi_simulator", "simulate", {"scenario": "B"})

    events = usage_store.load_events(feature="roi_simulator", parse_metadata=True)
    assert len(events) == 3
    assert isinstance(events.iloc[0]["metadata"], dict)

    summary = usage_store.summarize_events("roi_simulator")
    assert int(summary.iloc[0]["simulate"]) == 2
    assert int(summary.iloc[0]["download_ppt"]) == 1

    daily = usage_store.summarize_daily("roi_simulator")
    assert not daily.empty
    assert daily["count"].sum() == 3

    top = usage_store.top_metadata_entries("roi_simulator", "scenario")
    assert not top.empty
    assert top.iloc[0]["scenario"] == "A"
    assert int(top.iloc[0]["count"]) == 2
