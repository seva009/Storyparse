import unittest

from lolmake import format_message, tag_choice_made


class TestChoiceMadeTagging(unittest.TestCase):
    def test_tags_choice_when_bracketed_at_start(self):
        s = "[Принять подарок Лилит] Спасибо, Лилит, это именно то, что мне было нужно."
        got = format_message("YOU", s, lang="ru")
        self.assertEqual(
            got,
            "<PLAYER> <CHOICE_MADE> [Принять подарок Лилит] </CHOICE_MADE> Спасибо, Лилит, это именно то, что мне было нужно.",
        )

    def test_does_not_tag_system_note_style_choices(self):
        s = "Доступные варианты выбора: [1. Нагрубить Каллен, 2. Проигнорировать, 3. Попытаться договориться]"
        got = tag_choice_made(s)
        self.assertEqual(got, s)

    def test_tags_pipe_option_even_inside_multiline_text(self):
        s = "Текст до выбора.\nЗаплатить|Отдать 500 золотых.\nТекст после."
        got = tag_choice_made(s)
        self.assertIn("<CHOICE_MADE>", got)
        self.assertIn("Заплатить|Отдать 500 золотых.", got)

    def test_choice_short_label_prefers_left_side(self):
        from lolmake import _choice_short_label
        self.assertEqual(_choice_short_label("Согласиться|Хорошо, благодарю."), "Согласиться")

    def test_idempotent_when_already_tagged(self):
        s = "<CHOICE_MADE> [Принять подарок Лилит] </CHOICE_MADE> Спасибо."
        got = tag_choice_made(s)
        self.assertEqual(got, s)

    def test_keeps_text_without_choice_unchanged(self):
        s = "Спасибо, Лилит."
        got = format_message("YOU", s, lang="ru")
        self.assertEqual(got, "<PLAYER> Спасибо, Лилит.")


if __name__ == "__main__":
    unittest.main()

