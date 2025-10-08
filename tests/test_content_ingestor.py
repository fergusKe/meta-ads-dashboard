from pathlib import Path

import pandas as pd
import pytest

from utils import content_ingestor, template_store


@pytest.fixture()
def temp_template_env(tmp_path, monkeypatch):
    meta_path = tmp_path / "templates.parquet"
    storage_dir = tmp_path / "assets"
    ingest_log = tmp_path / "ingest.parquet"

    monkeypatch.setenv("TEMPLATE_METADATA_PATH", str(meta_path))
    monkeypatch.setenv("TEMPLATE_STORAGE_DIR", str(storage_dir))
    monkeypatch.setenv("TEMPLATE_INGEST_LOG_PATH", str(ingest_log))
    yield tmp_path


def test_ingest_dataframe_creates_records(temp_template_env):
    df = pd.DataFrame(
        [
            {
                "name": "夏季茶飲模板",
                "category": "茶飲",
                "format": "pptx",
                "tags": "夏季, 清爽",
                "description": "夏季促銷視覺模板",
                "price_type": "free",
            },
            {
                "name": "中秋禮盒廣告",
                "category": "節慶",
                "tags": ["中秋", "禮盒"],
                "price_type": "paid",
                "price": 199.0,
                "author": "Marketing Team",
            },
        ]
    )

    summary = content_ingestor.ingest_dataframe(df, defaults={"author": "Default Author"})

    assert summary.created == 2
    assert summary.updated == 0
    assert not summary.errors

    metadata = template_store.load_metadata()
    assert len(metadata) == 2
    assert sorted(metadata["name"]) == ["中秋禮盒廣告", "夏季茶飲模板"]
    record = metadata[metadata["name"] == "中秋禮盒廣告"].iloc[0]
    assert record["author"] == "Marketing Team"
    assert record["price"] == pytest.approx(199.0)


def test_ingest_dataframe_updates_existing_record(temp_template_env):
    df = pd.DataFrame(
        [
            {"template_id": "tpl_demo", "name": "宣傳圖模板", "category": "促銷", "price": 0},
        ]
    )
    content_ingestor.ingest_dataframe(df, defaults=None)

    update_df = pd.DataFrame(
        [
            {"template_id": "tpl_demo", "name": "宣傳圖模板", "category": "促銷", "price": 20},
        ]
    )
    summary = content_ingestor.ingest_dataframe(update_df, defaults=None)

    assert summary.created == 0
    assert summary.updated == 1

    metadata = template_store.load_metadata()
    assert metadata.iloc[0]["price"] == pytest.approx(20.0)


def test_ingest_from_files_handles_csv_and_attachments(temp_template_env):
    source_dir = temp_template_env / "source"
    source_dir.mkdir()
    csv_path = source_dir / "templates.csv"
    attachment = source_dir / "template.txt"
    attachment.write_text("demo", encoding="utf-8")

    df = pd.DataFrame(
        [
            {
                "name": "新品上市",
                "category": "新品",
                "file_path": str(attachment),
                "thumbnail_path": str(attachment),
            }
        ]
    )
    df.to_csv(csv_path, index=False)

    summary = content_ingestor.ingest_from_files([csv_path])

    assert summary.created == 1
    metadata = template_store.load_metadata()
    storage_path = metadata.iloc[0]["storage_path"]
    thumb_path = metadata.iloc[0]["thumbnail_path"]

    assert Path(storage_path).exists()
    assert Path(thumb_path).exists()
