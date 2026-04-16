import csv

def load_translation(path):
    data = {}
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Убираем префикс, если он есть
            line_id = row["id"].replace("line:", "")
            
            # Сохраняем все нужные колонки
            data[line_id] = {
                "node": row.get("node", ""),
                "zh": row.get("zh", ""),
                "en": row.get("en", ""),
                "ru": row.get("ru", "")
            }
    return data


def id_to_text(node_id, translation):
    raw_id = node_id.split(":")[-1]

    if raw_id in translation:
        return translation[raw_id]["en"]
    return ""
