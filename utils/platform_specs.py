from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd


DEFAULT_SPEC_PATH = "data/platform_specs.json"
DEFAULT_EXPORT_DIR = "data/exports"


@dataclass
class ConversionTemplate:
    platform: str
    format_name: str
    objective: str
    prompt: str
    checklist: List[str]


_DEFAULT_SPECS = [
    {
        "platform": "Meta",
        "ad_format": "Feed 圖像",
        "ratio": "1:1",
        "dimensions": "1080x1080",
        "max_duration": "N/A",
        "file_types": "JPG, PNG",
        "max_size": "30MB",
        "notes": "適用於 Facebook/Instagram 主頁貼文，建議圖中文字<20%",
    },
    {
        "platform": "Meta",
        "ad_format": "Reels 短影片",
        "ratio": "9:16",
        "dimensions": "1080x1920",
        "max_duration": "60 秒",
        "file_types": "MP4, MOV",
        "max_size": "4GB",
        "notes": "建議於前三秒呈現品牌，影片字幕需保留安全區域",
    },
    {
        "platform": "Google",
        "ad_format": "YouTube In-Stream",
        "ratio": "16:9",
        "dimensions": "1920x1080",
        "max_duration": "30 秒",
        "file_types": "MP4, MOV",
        "max_size": "4GB",
        "notes": "支援 skippable/非 skippable，需附加行動呼籲字詞",
    },
    {
        "platform": "LINE",
        "ad_format": "LINE VOOM 動畫",
        "ratio": "3:4",
        "dimensions": "1080x1440",
        "max_duration": "15 秒",
        "file_types": "MP4",
        "max_size": "500MB",
        "notes": "建議導入貼圖與品牌角色，影片需含字幕",
    },
    {
        "platform": "LINE",
        "ad_format": "LINE OA 圖文",
        "ratio": "1:1",
        "dimensions": "1040x1040",
        "max_duration": "N/A",
        "file_types": "JPG, PNG",
        "max_size": "10MB",
        "notes": "支援快速回覆按鈕，適合轉換活動",
    },
]

_DEFAULT_TEMPLATES: List[ConversionTemplate] = [
    ConversionTemplate(
        platform="Meta",
        format_name="Reels 短影片",
        objective="導購",
        prompt="""
你是廣告腳本編劇，請把以下品牌賣點轉換成 30 秒短影音腳本：
- 品牌：{brand}
- 主力產品：{product}
- 目標族群：{audience}
- 核心賣點：{value_prop}
請輸出：開場吸引語、主體段落、結尾 CTA。
""".strip(),
        checklist=[
            "前三秒呈現品牌識別",
            "內容中加入社群互動 CTA",
            "結尾提醒上滑或點擊購買",
        ],
    ),
    ConversionTemplate(
        platform="Google",
        format_name="YouTube In-Stream",
        objective="品牌曝光",
        prompt="""
請以 {brand} 的品牌語調撰寫 15 秒 YouTube In-Stream 廣告腳本，
需包含：引起注意的開場、品牌故事、行動呼籲。
""".strip(),
        checklist=[
            "5 秒前置介紹品牌 LOGO",
            "主文案不超過 60 字",
            "結尾加入網站或優惠碼",
        ],
    ),
    ConversionTemplate(
        platform="LINE",
        format_name="LINE OA 圖文",
        objective="導入 CRM",
        prompt="""
以 {brand} 的語氣撰寫 LINE 官方帳號推播文案，
需包含：主標題（20 字內）、引導文字、CTA 按鈕文案。
""".strip(),
        checklist=[
            "開頭打招呼並強調貼近感",
            "提供立即領取／體驗 CTA",
            "提醒點擊後的下一步流程",
        ],
    ),
]


def _spec_path() -> Path:
    path = os.getenv("PLATFORM_SPEC_PATH", DEFAULT_SPEC_PATH)
    return Path(path).expanduser()


def _ensure_storage() -> None:
    path = _spec_path()
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_default() -> None:
    _ensure_storage()
    path = _spec_path()
    if not path.exists():
        path.write_text(json.dumps(_DEFAULT_SPECS, ensure_ascii=False, indent=2), encoding="utf-8")


def load_specs() -> pd.DataFrame:
    _write_default()
    path = _spec_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = _DEFAULT_SPECS
    df = pd.DataFrame(data)
    return df


def filter_specs(platforms: Optional[Iterable[str]] = None, formats: Optional[Iterable[str]] = None) -> pd.DataFrame:
    df = load_specs()
    if platforms:
        df = df[df["platform"].isin(platforms)]
    if formats:
        df = df[df["ad_format"].isin(formats)]
    return df.reset_index(drop=True)


def list_conversion_templates() -> List[ConversionTemplate]:
    return _DEFAULT_TEMPLATES


def export_spec_bundle(selected: pd.DataFrame, output_dir: Optional[str] = None) -> Path:
    if selected.empty:
        raise ValueError("缺少要匯出的平台規格資料")

    export_dir = Path(output_dir or DEFAULT_EXPORT_DIR)
    export_dir.mkdir(parents=True, exist_ok=True)
    timestamp = pd.Timestamp.utcnow().strftime("%Y%m%d%H%M")
    bundle_path = export_dir / f"platform_specs_{timestamp}.zip"

    data = selected.to_dict(orient="records")
    templates = [t.__dict__ for t in _DEFAULT_TEMPLATES if t.platform in selected["platform"].unique()]

    import zipfile

    with zipfile.ZipFile(bundle_path, "w") as zf:
        zf.writestr("specs.json", json.dumps(data, ensure_ascii=False, indent=2))
        zf.writestr("templates.json", json.dumps(templates, ensure_ascii=False, indent=2))

    return bundle_path
