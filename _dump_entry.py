import json,re
from pathlib import Path
p = Path(__file__).parent / 'lilith_dataset_en.jsonl'
CHOICE_RE = re.compile(r'\[(.*?)\]')

with p.open(encoding='utf-8') as fh:
    for line in fh:
        data = json.loads(line)
        for m in data.get('messages', []):
            c = m.get('content','')
            if '<PLAYER>' in c and '<CHOICE_MADE>' in c:
                m_br = CHOICE_RE.search(c)
                if m_br:
                    br = m_br.group(1).strip()
                    if '1.' in br and ',' in br:
                        print('ENTRY:')
                        print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
                        raise SystemExit
print('done')
