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

    def test_shrinking_four_lines_uses_trailing_display_slots(self):
        # 82～85行の後に86～87行を2行で表示するなら
        # 84→86、85→87の置換時間を確認しなければならない。
        times = [(0, 100), (100, 200), (200, 400),
                 (300, 430), (350, 500), (450, 600)]
        replacements = _boundary_replacements(
            times, 0, 4, 4, 2, SETTINGS
        )
        self.assertEqual(
            [(item.previous_index, item.next_index) for item in replacements],
            [(2, 4), (3, 5)],
        )
        self.assertEqual(replacements[0].timing.available_ms, 0)
        self.assertEqual(replacements[0].overlap_ms, 500)

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

    def test_last_line_is_not_lost(self):
        self._plan([400 * i for i in range(15)])


if __name__ == "__main__":
    unittest.main()
