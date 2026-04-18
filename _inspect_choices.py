import json, re
from pathlib import Path

p = Path(__file__).parent / 'lilith_dataset_en.jsonl'
CHOICE_RE = re.compile(r'\[(.*?)\]')
OPTION_RE = re.compile(r'\d+\.\s*(.*?)(?=(?:,\s*\d+\.|\]|$))')

with p.open(encoding='utf-8') as fh:
    for i, line in enumerate(fh):
        data = json.loads(line)
        for m in data.get('messages', []):
            c = m.get('content','')
            if '<SYSTEM_NOTE>' in c and '[' in c and ']' in c:
                m_br = CHOICE_RE.search(c)
                if m_br and 'Morphean Paradox' in m_br.group(1):
                    sc = m_br.group(1)
                    opts = [o.strip() for o in OPTION_RE.findall(sc) if o.strip()]
                    print('--- SYSTEM CHOICE ---')
                    print(sc)
                    print('parsed options:', opts)
            if '<PLAYER>' in c and '<CHOICE_MADE>' in c:
                m_br = CHOICE_RE.search(c)
                if m_br and 'Morphean Paradox' in m_br.group(1):
                    print('PLAYER CHOICE MADE (contains Morphean Paradox):', m_br.group(1).strip())
