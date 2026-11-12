"""Read ruby-extended timed lyrics from RhythmicaLyrics .rlf edit files.

RLF is an HSP 'hspv' variable dump (not ZIP or plain text). The parser
validates array dimensions and reads without changing the original file.
"""
from __future__ import annotations

import re
import struct
from pathlib import Path

RECORD_SIZE = 72
RECORD_MAGIC = b"\xaa\x55\x40\x00"
SMALL_KANA = frozenset("ゃゅょぁぃぅぇぉゎャュョァィゥェォヮ＋")
RUBY_TIME = re.compile(r"\[\d{2}:\d{2}:\d{2}\]")


class RlfFormatError(ValueError):
    """Unsupported or damaged RhythmicaLyrics data."""


def _is_kanji(value: str) -> bool:
    return len(value) == 1 and ("\u3400" <= value <= "\u9fff" or value == "々")


def _ruby_text(reading: str, timings: str) -> str:
    units: list[str] = []
    for char in reading:
        if units and char in SMALL_KANA:
            units[-1] += char
        else:
            units.append(char)
    markers = RUBY_TIME.findall(timings)
    if len(markers) > max(0, len(units) - 1):
        raise RlfFormatError("ルビのタイムタグ数が文字数を超えています。")
    return "".join(
        (markers[i - 1] if i and i - 1 < len(markers) else "") + unit
        for i, unit in enumerate(units)
    )


def extract_rlf_lyrics(path: str | Path) -> str:
    path = Path(path)
    if path.stat().st_size > 128 * 1024 * 1024:
        raise RlfFormatError("RLFファイルが大きすぎます（128MBを超過）。")
    data = path.read_bytes()
    if not data.startswith(b"hspv"):
        raise RlfFormatError("RhythmicaLyricsのRLF形式ではありません。")

    names = (
        "mojitan", "mojisu", "t_jikan", "t_kazu", "mojitan_width",
        "sakura_timetag", "sakura_yomi",
    )
    positions = {}
    for name in names:
        offset = data.find(name.encode("ascii") + b"\x00")
        if offset < 0:
            raise RlfFormatError(f"RLF内に必要なデータ（{name}）がありません。")
        positions[name] = offset + len(name) + 1

    # mojisu is a 32-bit length for each lyric line.
    rows_data_size = (positions["t_jikan"] - len("t_jikan") - 1) - positions["mojisu"]
    if rows_data_size <= 0 or rows_data_size % 4:
        raise RlfFormatError("RLFの行数情報が不正です。")
    rows = rows_data_size // 4
    word_base = positions["mojitan"] + 2
    word_end = positions["mojisu"] - len("mojisu") - 1
    word_size = word_end - word_base + 2
    if not (0 < rows <= 10000) or word_size <= 0 or word_size % (rows * RECORD_SIZE):
        raise RlfFormatError("RLFの歌詞配列のサイズが不正です。")
    columns = word_size // (rows * RECORD_SIZE)
    stride = columns + 1

    numeric_size = (rows + 1) * stride * 4
    time_bytes = (positions["t_kazu"] - len("t_kazu") - 1) - positions["t_jikan"]
    count_bytes = (positions["mojitan_width"] - len("mojitan_width") - 1) - positions["t_kazu"]
    if time_bytes != numeric_size or count_bytes != numeric_size:
        raise RlfFormatError("RLFのタイムタグ配列のサイズが不正です。")

    ruby_base = positions["sakura_yomi"] + 2
    ruby_times_base = positions["sakura_timetag"] + 2

    def cell(base: int, item: int) -> str:
        offset = base + item * RECORD_SIZE
        if offset + RECORD_SIZE > len(data) or data[offset:offset + 4] != RECORD_MAGIC:
            raise RlfFormatError("RLFの文字配列の形式が不正です。")
        raw = data[offset + 6:offset + RECORD_SIZE].split(b"\x00", 1)[0]
        try:
            return raw.decode("cp932")
        except UnicodeDecodeError as exc:
            raise RlfFormatError("RLF内の文字をShift-JISで復号できません。") from exc

    def tag(row: int, col: int) -> str:
        item = row * stride + col
        value = struct.unpack_from("<i", data, positions["t_jikan"] + item * 4)[0]
        if value <= 0:
            return ""
        count = struct.unpack_from("<i", data, positions["t_kazu"] + item * 4)[0]
        minute, rest = divmod(value, 6000)
        second, centisecond = divmod(rest, 100)
        time = f"{minute:02d}:{second:02d}:{centisecond:02d}"
        return f"[{count}|{time}]" if count else f"[{time}]"

    lines = []
    for row in range(rows):
        length = struct.unpack_from("<i", data, positions["mojisu"] + row * 4)[0]
        if not (0 <= length < columns):
            raise RlfFormatError("RLFの歌詞行の長さが不正です。")

        words = [cell(word_base, col * rows + row) for col in range(length)]
        readings = [cell(ruby_base, row * stride + col) for col in range(length)]
        ruby_tags = [cell(ruby_times_base, row * stride + col) for col in range(length)]

        parts = []
        col = 0
        while col < length:
            if not readings[col]:
                parts.append(tag(row, col) + words[col])
                col += 1
                continue

            start = col
            phonetics = []
            while col < length:
                if readings[col]:
                    if (
                        col > start and not readings[col - 1].endswith("＋")
                        and not (words[start].isascii() and words[start].isalpha())
                    ):
                        break
                    phonetics.append(tag(row, col) + _ruby_text(readings[col], ruby_tags[col]))
                    col += 1
                elif (
                    words[start].isascii() and words[start].isalpha()
                    and words[col].isascii() and words[col].isalpha()
                    and not tag(row, col)
                ):
                    col += 1
                elif (
                    readings[col - 1].endswith("＋")
                    and _is_kanji(words[col])
                    and not tag(row, col)
                ):
                    # A kanji without its own reading can belong to a preceding ruby:
                    # 明日 => {明日|あす＋}.
                    col += 1
                else:
                    break
            parts.append("{" + "".join(words[start:col]) + "|" + "".join(phonetics) + "}")

        # The line-final [10|...] tag lives after the last lyric character.
        parts.append(tag(row, length))
        lines.append("".join(parts))
    return "\n".join(lines)
