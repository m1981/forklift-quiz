import json

def update_questions_with_hints(seed_file_path, mapping_file_path, output_file_path):
    # 1. Load seed data
    try:
        with open(seed_file_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
    except FileNotFoundError:
        print(f"Error: File {seed_file_path} not found.")
        return

    # 2. Load hint mapping
    try:
        with open(mapping_file_path, 'r', encoding='utf-8') as f:
            hint_data = json.load(f)
            heuristics = hint_data['heuristics']
            mapping = hint_data['mapping']
    except FileNotFoundError:
        print(f"Error: File {mapping_file_path} not found.")
        return

    # 3. Create a lookup dictionary: question_id -> hint_text
    id_to_hint = {}
    for key, question_ids in mapping.items():
        hint_text = heuristics.get(key, "")
        for q_id in question_ids:
            id_to_hint[q_id] = hint_text

    # 4. Update questions
    updated_count = 0
    for question in questions:
        q_id = question.get('id')
        if q_id in id_to_hint:
            question['hint'] = id_to_hint[q_id]
            updated_count += 1
        else:
            # Fallback if ID is missing in mapping (should not happen if mapping is complete)
            question['hint'] = None

    # 5. Save
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    print(f"Success! Added hints to {updated_count} questions. Saved to {output_file_path}")

if __name__ == "__main__":
    # Assuming you already ran the category update, we use v2 as input
    SEED_FILE = 'seed_questions.json'
    MAPPING_FILE = 'hint_mapping.json'
    OUTPUT_FILE = 'seed_questions_hints.json'

    update_questions_with_hints(SEED_FILE, MAPPING_FILE, OUTPUT_FILE)