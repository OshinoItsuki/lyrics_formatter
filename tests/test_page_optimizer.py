"""自動割付の回帰テスト。python -m unittest discover -s tests"""
import unittest

from app.services.page_optimizer import optimize_pages, _boundary_replacements


SETTINGS = {
    "pre_wipe_ms": 1500,
    "post_wipe_ms": 700,
    "interval_ms": 400,
    "effective_protection_ms": 350,
}


class AllocationRegressionTests(unittest.TestCase):
    def _plan(self, starts, max_lines=4):
        times = [(value, value + 80) for value in starts]
        plan = optimize_pages(times, SETTINGS, max_lines=max_lines,
                              paragraph_ranges=[(0, len(times) - 1)], base_lines=2)
        expected = 0
        for segment in plan.paragraphs:
            self.assertEqual(segment.start, expected, "歌詞行が重複・欠落している")
            self.assertGreaterEqual(segment.end, segment.start)
            expected = segment.end + 1
        self.assertEqual(expected, len(times))
        return plan

    def test_uniformly_spaced_lines_stay_at_two(self):
        plan = self._plan([400 * i for i in range(18)])
        self.assertTrue(all(seg.line_count == 2 for seg in plan.paragraphs))

    def test_short_gap_increases_lines_when_possible(self):
        plan = self._plan([100 * i for i in range(8)])
        self.assertTrue(any(seg.line_count > 2 for seg in plan.paragraphs))
        for seg in plan.paragraphs:
            for replacement in seg.replacements:
                self.assertEqual(replacement.timing.interval_ms, 400)

    def test_localized_short_gap_does_not_lock_rest_to_three(self):
        starts = [0, 400, 800, 900, 1000, 1400, 1800, 2200,
                  2600, 3000, 3400, 3800, 4200, 4600]
        plan = self._plan(starts)
        self.assertTrue(any(seg.line_count > 2 for seg in plan.paragraphs))
        self.assertEqual(plan.paragraphs[-1].line_count, 2)

    def test_resizing_compares_full_previous_and_next_pages(self):
        # 3→4行なら、前ページ最後の歌詞と次ページ最初の歌詞が
        # 重なっていないかを検査する。
        times = [
            (0, 100), (100, 200), (200, 700),
            (600, 800), (900, 1000), (1100, 1200), (1300, 1400),
        ]
        replacements = _boundary_replacements(
            times, 0, 3, 3, 4, SETTINGS
        )
        self.assertEqual(len(replacements), 1)
        self.assertEqual(
            (replacements[0].previous_index, replacements[0].next_index),
            (2, 3),
        )
        self.assertEqual(replacements[0].overlap_ms, 1000)

    def test_shrinking_compares_full_previous_and_next_pages(self):
        times = [
            (0, 100), (100, 200), (200, 400),
            (300, 430), (350, 500), (450, 600),
        ]
        replacements = _boundary_replacements(
            times, 0, 4, 4, 2, SETTINGS
        )
        self.assertEqual(len(replacements), 1)
        self.assertEqual(
            (replacements[0].previous_index, replacements[0].next_index),
            (3, 4),
        )
        self.assertEqual(replacements[0].overlap_ms, 800)

    def test_expanding_uses_new_slots_before_reusing_old_positions(self):
        # 2→3行では先頭1行が増設枠を使用し、
        # 既存2行は次ページの後ろ2行と時間を比較する。
        times = [
            (38406, 38726), (38678, 38983),
            (38995, 39706), (39434, 39630), (39643, 40250),
        ]
        replacements = _boundary_replacements(
            times, 0, 2, 2, 3, SETTINGS
        )
        self.assertEqual(
            [(item.previous_index, item.next_index)
             for item in replacements],
            [(0, 3), (1, 4)],
        )
        self.assertTrue(all(item.overlap_ms == 0 for item in replacements))

    def test_actual_six_line_case_prefers_three_plus_three(self):
        # 実例の82～87行付近のタイムタグ（単位: 1/100秒）。
        times = [
            (38995, 39706),  # 82
            (39334, 39630),  # 83
            (39643, 40250),  # 84
            (39989, 40189),  # 85
            (40200, 40436),  # 86
            (40445, 41127),  # 87
        ]
        plan = optimize_pages(
            times, SETTINGS, max_lines=4,
            paragraph_ranges=[(0, 5)], base_lines=2,
        )
        self.assertEqual(
            [(segment.start, segment.end, segment.line_count)
             for segment in plan.paragraphs],
            [(0, 5, 3)],
        )
        self.assertFalse(any(
            replacement.overlap_ms > 0
            for segment in plan.paragraphs
            for replacement in segment.replacements
        ))

    def test_full_sample_keeps_two_lines_until_local_change(self):
        # 利用者の歌詞の56～87行からタイムタグだけ抽出した回帰ケース。
        # 前半を不必要に4行化せず、82～87行は3行＋3行にする。
        times = [
            (29320, 29841), (29874, 30396), (30428, 30668), (30711, 30937),
            (30988, 31221), (31267, 31509), (31531, 32001), (32034, 32675),
            (32649, 33115), (33132, 33408), (33419, 33630), (33588, 33992),
            (34007, 34314), (34323, 34690), (34669, 35171), (35124, 35423),
            (35438, 35805), (35786, 36262), (36084, 36843), (36608, 36912),
            (36990, 37280), (37290, 37597), (37566, 38135), (38127, 38396),
            (38406, 38726), (38678, 38983), (38995, 39706), (39434, 39630),
            (39643, 40250), (39989, 40189), (40200, 40436), (40445, 41127),
        ]
        plan = optimize_pages(
            times, SETTINGS, max_lines=4,
            paragraph_ranges=[(0, len(times) - 1)], base_lines=2,
        )
        page_starts = []
        for segment in plan.paragraphs:
            page_starts.extend(
                (index + 56, segment.line_count)
                for index in range(segment.start, segment.end + 1, segment.line_count)
            )
        # 76～81行は2+2+2、82～87行は3+3であること。
        self.assertIn((76, 2), page_starts)
        self.assertIn((78, 2), page_starts)
        self.assertIn((80, 2), page_starts)
        self.assertIn((82, 3), page_starts)
        self.assertIn((85, 3), page_starts)
        self.assertNotIn((76, 3), page_starts)
        self.assertNotIn((79, 3), page_starts)
        self.assertTrue(all(size == 2 for first, size in page_starts if first < 76))
        self.assertNotIn((84, 4), page_starts)

    def test_last_line_is_not_lost(self):
        self._plan([400 * i for i in range(15)])


if __name__ == "__main__":
    unittest.main()
