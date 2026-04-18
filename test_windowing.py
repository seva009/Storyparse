import unittest

import lolmake


class TestWindowing(unittest.TestCase):
    def setUp(self):
        self._orig_find_window_size = lolmake.find_window_size
        self._orig_estimate_tokens = lolmake.estimate_tokens

    def tearDown(self):
        lolmake.find_window_size = self._orig_find_window_size
        lolmake.estimate_tokens = self._orig_estimate_tokens

    def _mk_blocks(self, n):
        # Minimal blocks that build_example will accept.
        out = []
        for i in range(n):
            role = "YOU" if (i % 2 == 0) else "LILITH"
            out.append({"role": role, "lines": [f"line {i}"], "scene": None, "emotion": None})
        return out

    def test_short_dialogue_not_sliced(self):
        lolmake.find_window_size = lambda token_counts, max_tokens: 10
        lolmake.estimate_tokens = lambda s: 1
        blocks = self._mk_blocks(6)
        ex = lolmake.blocks_to_examples(blocks, "SYS", "ru")
        self.assertEqual(len(ex), 1)

    def test_long_dialogue_fixed_windows_stop_at_right_edge(self):
        # window_size=10 => step=2 (short window)
        lolmake.find_window_size = lambda token_counts, max_tokens: 10
        lolmake.estimate_tokens = lambda s: 1
        blocks = self._mk_blocks(25)
        ex = lolmake.blocks_to_examples(blocks, "SYS", "ru")
        # Starts: 0,2,4,6,8,10,12,14 plus forced final start=15
        self.assertEqual(len(ex), 9)

    def test_step_is_5_for_large_window(self):
        # window_size=20 => step=5
        lolmake.find_window_size = lambda token_counts, max_tokens: 20
        lolmake.estimate_tokens = lambda s: 1
        blocks = self._mk_blocks(60)
        ex = lolmake.blocks_to_examples(blocks, "SYS", "ru")
        # last_start=40, starts 0..40 step5 => 9 windows
        self.assertEqual(len(ex), 9)

    def test_window_does_not_split_choice_pair(self):
        # Force small window to make splitting likely.
        lolmake.find_window_size = lambda token_counts, max_tokens: 4
        lolmake.estimate_tokens = lambda s: 1
        blocks = [
            {"role": "YOU", "lines": ["a"], "scene": None, "emotion": None},
            {"role": "SYSTEM", "lines": ["Доступные варианты выбора: [1. Да, 2. Нет]"], "scene": None, "emotion": None},
            {"role": "YOU", "lines": [f"{lolmake.CHOICE_MADE_OPEN} [Да] {lolmake.CHOICE_MADE_CLOSE}"], "scene": None, "emotion": None},
            {"role": "LILITH", "lines": ["b"], "scene": None, "emotion": None},
            {"role": "YOU", "lines": ["c"], "scene": None, "emotion": None},
            {"role": "LILITH", "lines": ["d"], "scene": None, "emotion": None},
        ]
        ex = lolmake.blocks_to_examples(blocks, "SYS", "ru")
        for e in ex:
            # no CHOICE_MADE should appear without the system note in the same example
            content = "\n".join(m["content"] for m in e["messages"])
            if "<CHOICE_MADE>" in content:
                self.assertIn("Доступные варианты выбора", content)


if __name__ == "__main__":
    unittest.main()

