import json
import os
import re
import unittest


class TestDatasetChoiceCoverage(unittest.TestCase):
    """
    Verify that when a SYSTEM_NOTE lists numbered choices, each listed option
    appears at least once in the dataset as a '<PLAYER> <CHOICE_MADE> [option]'

    This test uses only the built dataset file (no parsing or graph building).
    It looks for a specific example choice block (the one mentioned by the user)
    and checks coverage across the entire dataset file.
    """

    # Check all language datasets
    DATASET_FILES = {
        'en': os.path.join(os.path.dirname(__file__), 'lilith_dataset_en.jsonl'),
        'ru': os.path.join(os.path.dirname(__file__), 'lilith_dataset_ru.jsonl'),
        'zh': os.path.join(os.path.dirname(__file__), 'lilith_dataset_zh.jsonl'),
    }

    CHOICE_RE = re.compile(r'\[(.*?)\]')
    OPTION_RE = re.compile(r'\d+\.\s*(.*?)(?=(?:,\s*\d+\.|\]|$))')

    def test_all_listed_options_are_chosen_in_each_dataset(self):
        """
        For each language dataset, find every SYSTEM_NOTE that lists numbered choices
        (bracketed), parse the listed options, and ensure each listed option appears at
        least once in the same dataset as a '<PLAYER> <CHOICE_MADE> [option]'.
        This test must fail if any listed option is never chosen in that dataset.
        """
        failures = []

        for lang, path in self.DATASET_FILES.items():
            if not os.path.exists(path):
                self.skipTest(f"Dataset file not found: {path}")

            with open(path, encoding='utf-8') as fh:
                lines = [json.loads(l) for l in fh]

            # collect all system-note bracket contents and all player choice-made texts
            system_choices = []
            player_choice_made_texts = []

            for entry in lines:
                for m in entry.get('messages', []):
                    c = m.get('content', '')
                    if '<SYSTEM_NOTE>' in c and '[' in c and ']' in c:
                        m_br = self.CHOICE_RE.search(c)
                        if m_br:
                            bracket = m_br.group(1)
                            system_choices.append(bracket)
                    # collect any explicit <CHOICE_MADE> occurrences regardless of whether
                    # they appear in the same message as a <PLAYER> tag. Some dataset
                    # entries emit <CHOICE_MADE> in their own message blocks.
                    if '<CHOICE_MADE>' in c:
                        # extract the bracket specifically from inside the <CHOICE_MADE> tag
                        for m_br in re.finditer(r'<CHOICE_MADE>\s*\[(.*?)\]', c, re.DOTALL):
                            player_choice_made_texts.append(m_br.group(1).strip())

            # For every system choice, parse options and check coverage
            for sc in system_choices:
                opts = [o.strip() for o in self.OPTION_RE.findall(sc) if o.strip()]
                # If there were no numbered options (e.g. single option lists), skip
                if not opts:
                    continue
                missing = []
                for opt in opts:
                    found = any(opt == pc or opt in pc or pc in opt for pc in player_choice_made_texts)
                    if not found:
                        missing.append(opt)
                if missing:
                    failures.append({'lang': lang, 'system_choice': sc, 'missing': missing, 'parsed': opts})

        if failures:
            # Build a concise failure message showing a few example misses
            msgs = []
            for f in failures[:10]:
                msgs.append(f"[{f['lang']}] missing {f['missing']} from system_choice: {f['system_choice']}")
            self.fail("Some listed choice options were never chosen in datasets:\n" + "\n".join(msgs))


if __name__ == '__main__':
    unittest.main()
