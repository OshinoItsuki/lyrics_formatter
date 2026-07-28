from __future__ import annotations

import json
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class NicoKaraTimingSettings:
    maker_version: int
    source_addon: str
    pre_wipe_ms: int
    post_wipe_ms: int
    interval_ms: int
    manual_protection_enabled: bool
    manual_protection_ms: int

    @property
    def effective_protection_ms(self) -> int:
        if self.manual_protection_enabled:
            return self.manual_protection_ms
        return min(self.pre_wipe_ms, self.post_wipe_ms) // 2

    def to_dict(self) -> dict:
        data = asdict(self)
        data["effective_protection_ms"] = self.effective_protection_ms
        return data


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _xml_values(raw: bytes) -> dict[str, str]:
    root = ET.fromstring(raw.decode("utf-8-sig"))
    return {_local_name(e.tag): (e.text or "") for e in root.iter()}


def _bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _find_selected_id_v2(raw: bytes, key: str) -> str | None:
    values = _xml_values(raw)
    return values.get(key) or None


def _find_selected_id_v3(data: object, key: str) -> str | None:
    if isinstance(data, dict):
        if key in data and isinstance(data[key], str):
            return data[key]
        for value in data.values():
            found = _find_selected_id_v3(value, key)
            if found:
                return found
    elif isinstance(data, list):
        for value in data:
            found = _find_selected_id_v3(value, key)
            if found:
                return found
    return None


def load_sta(path: str) -> NicoKaraTimingSettings:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(path)

    with zipfile.ZipFile(source) as archive:
        names = set(archive.namelist())

        v3_main = "NicoKaraMaker3/Nkm3Settings.json"
        v2_main = "NicoKaraMaker2/Nkm2Settings.config"

        if v3_main in names:
            version = 3
            main = json.loads(archive.read(v3_main).decode("utf-8-sig"))
            selected = (
                _find_selected_id_v3(main, "ShowTimeAdjusterId")
                or _find_selected_id_v3(main, "LastSelectedShowTimeAdjusterId")
                or _find_selected_id_v3(main, "LineBreakerId")
                or "SHINTA.EmptyLineBreaker"
            )
            candidates = [
                f"NicoKaraMaker3/AddOns/{selected}.json",
                "NicoKaraMaker3/AddOns/SHINTA.EmptyLineBreaker.json",
            ]
            target = next((name for name in candidates if name in names), None)
            if target is None:
                target = next((n for n in names if n.endswith(".json") and "AddOns/" in n and b'"PreTime2"' in archive.read(n)), None)
            if target is None:
                raise ValueError("表示時間設定を含むJSONが見つかりません。")
            values = json.loads(archive.read(target).decode("utf-8-sig"))
            addon = Path(target).stem

        elif v2_main in names:
            version = 2
            main_raw = archive.read(v2_main)
            selected = (
                _find_selected_id_v2(main_raw, "LastSelectedShowTimeAdjusterId")
                or _find_selected_id_v2(main_raw, "LastSelectedLineBreakerId")
                or "SHINTA.EmptyLineBreaker"
            )
            candidates = [
                f"NicoKaraMaker2/AddOns/{selected}.config",
                "NicoKaraMaker2/AddOns/SHINTA.EmptyLineBreaker.config",
            ]
            target = next((name for name in candidates if name in names), None)
            if target is None:
                target = next((n for n in names if n.endswith(".config") and "AddOns/" in n and b"PreTime2" in archive.read(n)), None)
            if target is None:
                raise ValueError("表示時間設定を含むXMLが見つかりません。")
            values = _xml_values(archive.read(target))
            addon = Path(target).stem

        else:
            raise ValueError("ニコカラメーカー2/3の設定バックアップとして判別できません。")

    try:
        result = NicoKaraTimingSettings(
            maker_version=version,
            source_addon=addon,
            pre_wipe_ms=int(values["PreTime2"]),
            post_wipe_ms=int(values["PostTime2"]),
            interval_ms=int(values["IntervalTime2"]),
            manual_protection_enabled=_bool(values.get("DoesSetProtectTime", False)),
            manual_protection_ms=int(values.get("ManualProtectTime", 0)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("設定ファイルの表示時間項目を読み取れませんでした。") from exc

    if result.manual_protection_ms < 0:
        raise ValueError("表示保護時間が不正です。")
    if result.manual_protection_enabled and result.manual_protection_ms > min(result.pre_wipe_ms, result.post_wipe_ms):
        raise ValueError("手動表示保護時間がワイプ前後の表示時間を超えています。")
    return result
