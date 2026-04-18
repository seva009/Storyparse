import json
import os
import tempfile
import unittest

from graph import build_graph
from translate import load_translation
from lolmake import extract_yarn_metadata, find_components, save_dataset


class TestLilithNotUser(unittest.TestCase):
    def test_no_lilith_content_in_user_messages(self):
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
                        role = m.get("role")
                        content = m.get("content", "")
                        # If the content contains a Lilith character tag, it must NOT be a user message.
                        # System content may mention <CHAR_Lilith> (prompts/instructions), so only fail
                        # when that tag appears in a user-labelled message.
                        if "<CHAR_Lilith>" in content:
                            self.assertNotEqual(role, "user", f"Found <CHAR_Lilith> in a user role: {role}\n{content}")


if __name__ == "__main__":
    unittest.main()
