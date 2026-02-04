import json


def update_categories_simple(file_path: str) -> None:
    """Prosta wersja - nadpisuje oryginalny plik"""

    mapping = {
        "przepisy": list(range(1, 63)) + list(range(67, 73)),
        "budowa-techniczna": list(range(73, 126))
        + list(range(127, 176))
        + list(range(179, 217)),
        "diagramy": [77, 78] + list(range(183, 245)),
    }

    # Odwrotne mapowanie
    id_map = {}
    for cat, ids in mapping.items():
        for id_ in ids:
            id_map[id_] = cat

    # Wczytaj i aktualizuj
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    for q in data:
        q_id = int(q["id"])
        if q_id in id_map:
            q["category"] = id_map[q_id]

    # Zapisz
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✓ Kategorie zaktualizowane!")


# Użycie:
update_categories_simple("questions.json")
