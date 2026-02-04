import json


def update_questions_with_categories(
    seed_file_path: str, mapping_file_path: str, output_file_path: str
) -> None:
    # 1. Load the seed data
    try:
        with open(seed_file_path, encoding="utf-8") as f:
            questions = json.load(f)
    except FileNotFoundError:
        print(f"Error: File {seed_file_path} not found.")
        return

    # 2. Load the category mapping
    try:
        with open(mapping_file_path, encoding="utf-8") as f:
            category_map = json.load(f)
    except FileNotFoundError:
        print(f"Error: File {mapping_file_path} not found.")
        return

    # 3. Invert the mapping for O(1) lookup complexity
    # Transforms: {"Category A": ["1", "2"]} -> {"1": "Category A", "2": "Category A"}
    id_to_category = {}
    for category, ids in category_map.items():
        for q_id in ids:
            id_to_category[q_id] = category

    # 4. Update the question objects
    updated_count = 0
    for question in questions:
        q_id = question.get("id")
        if q_id in id_to_category:
            question["category"] = id_to_category[q_id]
            updated_count += 1
        else:
            # Optional: Handle questions without a category
            question["category"] = "Uncategorized"
            print(f"Warning: Question ID {q_id} has no category mapping.")

    # 5. Save the updated JSON
    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    print(f"Success! Updated {updated_count} questions. Saved to {output_file_path}")


if __name__ == "__main__":
    # Define your file paths here
    SEED_FILE = "seed_questions.json"
    MAPPING_FILE = "mapping_category.json"
    OUTPUT_FILE = "seed_questions_categories.json"

    update_questions_with_categories(SEED_FILE, MAPPING_FILE, OUTPUT_FILE)
