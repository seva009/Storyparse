import json
import os
import tempfile
import unittest

from graph import build_graph
from translate import load_translation
from lolmake import extract_yarn_metadata, find_components, save_dataset


class TestDatasetChoiceTagging(unittest.TestCase):
    def test_built_ru_dataset_contains_choice_made_tags(self):
        base = os.path.dirname(__file__)
        yarn_folder = os.path.join(base, "yarn_scripts")
        translation_csv = os.path.join(base, "en_ru_pairs.csv")

        graph = build_graph(yarn_folder)
        translation = load_translation(translation_csv)
        node_bg, node_emotion = extract_yarn_metadata(yarn_folder)
        components = find_components(graph, translation)

        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "out_ru.jsonl")
            save_dataset(components, translation, node_bg, node_emotion, out, lang="ru")

            found = False
            found_any_system_choice_note = False
            with open(out, encoding="utf-8") as f:
                for line in f:
                    obj = json.loads(line)
                    for m in obj.get("messages", []):
                        c = m.get("content", "")
                        if "<CHOICE_MADE>" in c:
                            found = True
                        if "<SYSTEM_NOTE>" in c and "Доступные варианты выбора" in c:
                            found_any_system_choice_note = True
                    if found and found_any_system_choice_note:
                        break

            self.assertTrue(found_any_system_choice_note, "Expected at least one <SYSTEM_NOTE> with available choices")
            self.assertTrue(found, "Expected at least one <CHOICE_MADE> tag in built dataset output")

    def test_built_ru_dataset_does_not_leave_raw_pipe_options(self):
        """
        Ensure we don't leave untagged 'Option|Desc' lines in player/thought messages.
        System notes may still include a compact list, but player content should not
        contain raw pipe options outside <CHOICE_MADE>.
        """
        base = os.path.dirname(__file__)
        yarn_folder = os.path.join(base, "yarn_scripts")
        translation_csv = os.path.join(base, "en_ru_pairs.csv")

        graph = build_graph(yarn_folder)
        translation = load_translation(translation_csv)
        node_bg, node_emotion = extract_yarn_metadata(yarn_folder)
        components = find_components(graph, translation)

        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "out_ru.jsonl")
            save_dataset(components, translation, node_bg, node_emotion, out, lang="ru")

            with open(out, encoding="utf-8") as f:
                for line in f:
                    obj = json.loads(line)
                    for m in obj.get("messages", []):
                        c = m.get("content", "")
                        if "<PLAYER>" in c and "|" in c:
                            # If there's a pipe inside player content, it must be inside CHOICE_MADE.
                            self.assertIn("<CHOICE_MADE>", c)

    def test_choice_note_is_followed_by_choice_made_once(self):
        """
        For every <SYSTEM_NOTE> with available choices, ensure we emit exactly one
        immediate <CHOICE_MADE> line right after it in the same user content.
        """
        base = os.path.dirname(__file__)
        yarn_folder = os.path.join(base, "yarn_scripts")
        translation_csv = os.path.join(base, "en_ru_pairs.csv")

        graph = build_graph(yarn_folder)
        translation = load_translation(translation_csv)
        node_bg, node_emotion = extract_yarn_metadata(yarn_folder)
        components = find_components(graph, translation)

        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "out_ru.jsonl")
            save_dataset(components, translation, node_bg, node_emotion, out, lang="ru")

            with open(out, encoding="utf-8") as f:
                for line in f:
                    obj = json.loads(line)
                    for m in obj.get("messages", []):
                        c = m.get("content", "")
                        if "<SYSTEM_NOTE>" not in c or "Доступные варианты выбора" not in c:
                            continue
                        lines = [ln.strip() for ln in c.splitlines() if ln.strip()]
                        for idx, ln in enumerate(lines):
                            if ln.startswith("<SYSTEM_NOTE>") and "Доступные варианты выбора" in ln:
                                # Next non-empty line must be a single CHOICE_MADE player line
                                if idx + 1 >= len(lines):
                                    self.fail("SYSTEM_NOTE choices without following line")
                                nxt = lines[idx + 1]
                                self.assertTrue(nxt.startswith("<PLAYER> <CHOICE_MADE>"), f"Expected CHOICE_MADE after SYSTEM_NOTE, got: {nxt}")
                                # And do not duplicate immediately
                                if idx + 2 < len(lines):
                                    self.assertFalse(lines[idx + 2].startswith("<PLAYER> <CHOICE_MADE>"), "Duplicate CHOICE_MADE line detected")

    def test_if_refuse_is_offered_it_is_sometimes_chosen(self):
        """
        If dataset contains choices that offer "Отказаться", ensure at least one
        CHOICE_MADE picks it across our multiple walks (min/max).
        """
        base = os.path.dirname(__file__)
        yarn_folder = os.path.join(base, "yarn_scripts")
        translation_csv = os.path.join(base, "en_ru_pairs.csv")

        graph = build_graph(yarn_folder)
        translation = load_translation(translation_csv)
        node_bg, node_emotion = extract_yarn_metadata(yarn_folder)
        components = find_components(graph, translation)

        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "out_ru.jsonl")
            save_dataset(components, translation, node_bg, node_emotion, out, lang="ru")

            offered = 0
            chosen_refuse = 0
            with open(out, encoding="utf-8") as f:
                for line in f:
                    obj = json.loads(line)
                    for m in obj.get("messages", []):
                        c = m.get("content", "")
                        if "<SYSTEM_NOTE>" in c and "Доступные варианты выбора" in c and "Отказаться" in c:
                            offered += 1
                        if "<PLAYER> <CHOICE_MADE>" in c and "[Отказаться]" in c:
                            chosen_refuse += 1

            if offered > 0:
                self.assertGreater(chosen_refuse, 0, "Refuse was offered but never chosen in dataset output")


if __name__ == "__main__":
    unittest.main()

