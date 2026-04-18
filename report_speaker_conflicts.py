"""
Scan the graph and translation table for speaker-name conflicts across en/ru/zh.
Prints a short report and writes full details to /tmp/speaker_conflicts.json
"""
import json
from translate import load_translation
from graph import build_graph
from text import detect_speaker, normalize_speaker
import os


def analyze(graph, translation):
    conflicts = []
    for node in graph.nodes.values():
        raw_id = node.id.split(":")[-1]
        if raw_id not in translation:
            continue
        tr = translation[raw_id]
        texts = [('en', tr.get('en','') or ''), ('ru', tr.get('ru','') or ''), ('zh', tr.get('zh','') or '')]
        candidates = []
        for lang, txt in texts:
            if not txt:
                continue
            sp = detect_speaker(txt)
            if sp and sp != 'THOUGHT':
                candidates.append((lang, sp.strip()))

        # Unique by name
        seen = set()
        uniq = []
        for lang, name in candidates:
            if name not in seen:
                seen.add(name)
                uniq.append((lang, name))

        if len(uniq) <= 1:
            continue

        norms = [normalize_speaker(n) for _, n in uniq]
        if len(set(norms)) > 1:
            conflicts.append({'node_id': node.id, 'names': uniq, 'norms': norms})

    return conflicts


def main():
    base = os.path.dirname(__file__)
    yarn_folder = os.path.join(base, 'yarn_scripts')
    translation_csv = os.path.join(base, 'en_ru_pairs.csv')

    print('Building graph...')
    graph = build_graph(yarn_folder)
    print('Loading translations...')
    translation = load_translation(translation_csv)

    print('Scanning for speaker conflicts...')
    confs = analyze(graph, translation)
    print(f'Found {len(confs)} conflicts')
    if confs:
        sample = confs[:30]
        for c in sample:
            print(c['node_id'], '->', c['names'], 'norms:', c['norms'])

    out = '/tmp/speaker_conflicts.json'
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(confs, fh, ensure_ascii=False, indent=2)
    print('Full report written to', out)


if __name__ == '__main__':
    main()
