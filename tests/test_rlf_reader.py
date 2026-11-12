"""RLF parser checks without committing any copyrighted sample lyrics."""
import struct
import tempfile
import unittest
from pathlib import Path

from app.services.rlf_reader import RlfFormatError, _ruby_text, extract_rlf_lyrics


def _record(value=""):
    raw = value.encode("cp932")
    if len(raw) > 66:
        raise ValueError("test record overflow")
    return b"\xaa\x55\x40\x00\x00\x00" + raw.ljust(66, b"\x00")


def _minimal_rlf():
    """A tiny in-memory HSP variable dump with the same array layout."""
    rows, columns = 2, 8
    width = columns + 1
    cells = (rows + 1) * width
    data = bytearray(b"hspv" + b"\x00" * 12)

    data.extend(b"mojitan\x00\x00\x00")
    words = ["(", "美", ")", "こ", "闇", "\r\n"]
    for col in range(columns):
        for row in range(rows):
            value = (words[col] if col < len(words) else "") if row == 0 else ("\r\n" if col == 0 else "")
            data.extend(_record(value))
    del data[-2:]  # HSP string arrays share their trailing padding with the next name.

    data.extend(b"mojisu\x00")
    data.extend(struct.pack("<2i", 5, 0))

    stamp = [0] * cells
    counts = [0] * cells
    for pos, time, count in [(3, 100, 1), (4, 120, 2), (5, 150, 10)]:
        stamp[pos], counts[pos] = time, count

    data.extend(b"t_jikan\x00")
    data.extend(struct.pack("<" + "i" * cells, *stamp))
    data.extend(b"t_kazu\x00")
    data.extend(struct.pack("<" + "i" * cells, *counts))
    data.extend(b"mojitan_width\x00")
    data.extend(b"\x00" * (rows * columns * 4))

    for name, content in [
        ("sakura_timetag", "[00:01:30]"),
        ("sakura_yomi", "やみ"),
    ]:
        data.extend(name.encode() + b"\x00\x00\x00")
        for i in range(cells):
            data.extend(_record(content if i == 4 else ""))
        del data[-2:]
    return bytes(data)


class RlfReaderTests(unittest.TestCase):
    def test_phonetic_units_keep_small_kana_together(self):
        self.assertEqual(
            _ruby_text("じゅう＋", "[00:01:20]"),
            "じゅ[00:01:20]う＋",
        )

    def test_extract_preserves_ruby_tags_and_blank_lines(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "test.rlf"
            original = _minimal_rlf()
            path.write_bytes(original)
            self.assertEqual(
                extract_rlf_lyrics(path),
                "(美)[1|00:01:00]こ{闇|[2|00:01:20]や[00:01:30]み}[10|00:01:50]\n",
            )
            self.assertEqual(path.read_bytes(), original)

    def test_invalid_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.rlf"
            path.write_bytes(b"not a valid rlf")
            with self.assertRaises(RlfFormatError):
                extract_rlf_lyrics(path)


if __name__ == "__main__":
    unittest.main()
