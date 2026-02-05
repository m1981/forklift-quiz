import json


def filter_json_fields(input_file: str, output_file: str) -> None:
    """
    Parse JSON file and output only specified fields: id, text, options, hint, category

    Args:
        input_file: Path to input JSON file
        output_file: Path to output JSON file
    """
    # Read input JSON
    with open(input_file, encoding="utf-8") as f:
        data = json.load(f)

    # Filter fields
    filtered_data = []
    for item in data:
        filtered_item = {
            "id": item.get("id"),
            "text": item.get("text"),
            "options": item.get("options"),
            "hint": item.get("hint"),
            "category": item.get("category"),
        }
        filtered_data.append(filtered_item)

    # Write output JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=2)

    print(f"Filtered {len(filtered_data)} items successfully!")


# Usage
if __name__ == "__main__":
    filter_json_fields("seed_questions.json", "output.json")
