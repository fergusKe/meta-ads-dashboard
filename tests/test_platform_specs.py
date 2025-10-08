from utils import platform_specs


def test_platform_specs_load_and_export(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_SPEC_PATH", str(tmp_path / "specs.json"))
    df = platform_specs.load_specs()
    assert not df.empty
    filtered = platform_specs.filter_specs([df.iloc[0]["platform"]], None)
    bundle = platform_specs.export_spec_bundle(filtered, output_dir=tmp_path.as_posix())
    assert bundle.exists()
    templates = platform_specs.list_conversion_templates()
    assert templates
