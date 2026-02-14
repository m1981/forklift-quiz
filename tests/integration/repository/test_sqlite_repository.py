from unittest.mock import patch

from src.quiz.domain.models import Language, OptionKey, Question


class TestSQLiteRepository:
    def test_is_empty_returns_true_initially(self, in_memory_repo):
        print("\n--- TEST: is_empty ---")
        result = in_memory_repo.is_empty()
        print(f"Result: {result}")
        assert result is True

    def test_seed_questions_inserts_data(self, in_memory_repo, sample_question):
        print("\n--- TEST: seed_questions ---")
        in_memory_repo.seed_questions([sample_question])

        is_empty = in_memory_repo.is_empty()
        print(f"Is Empty after seed: {is_empty}")
        assert is_empty is False

        fetched = in_memory_repo.get_questions_by_ids([sample_question.id])
        print(f"Fetched count: {len(fetched)}")
        assert len(fetched) == 1
        assert fetched[0].text == sample_question.text

    def test_get_or_create_profile_creates_new(self, in_memory_repo):
        print("\n--- TEST: get_or_create_profile (NEW) ---")
        user_id = "new_user"

        # 1. Check DB before
        conn = in_memory_repo._get_connection()
        cursor = conn.execute(
            "SELECT count(*) FROM user_profiles WHERE user_id=?", (user_id,)
        )
        print(f"Count before: {cursor.fetchone()[0]}")

        # 2. Act
        profile = in_memory_repo.get_or_create_profile(user_id)
        print(f"Profile returned: {profile}")

        # 3. Check DB after
        cursor = conn.execute(
            "SELECT count(*) FROM user_profiles WHERE user_id=?", (user_id,)
        )
        count_after = cursor.fetchone()[0]
        print(f"Count after: {count_after}")

        assert count_after == 1
        assert profile.user_id == user_id
        assert profile.streak_days == 1
        # This was the failure point:
        print(f"Onboarding status: {profile.has_completed_onboarding}")
        assert profile.has_completed_onboarding is False

    def test_save_profile_updates_data(self, in_memory_repo):
        print("\n--- TEST: save_profile ---")
        user_id = "existing_user"
        profile = in_memory_repo.get_or_create_profile(user_id)

        profile.preferred_language = Language.EN
        profile.has_completed_onboarding = True
        profile.daily_progress = 5

        print(f"Saving profile: {profile}")
        in_memory_repo.save_profile(profile)

        updated = in_memory_repo.get_or_create_profile(user_id)
        print(f"Fetched updated: {updated}")

        assert updated.preferred_language == Language.EN
        assert updated.has_completed_onboarding is True
        assert updated.daily_progress == 5

    def test_save_attempt_updates_mastery_logic(self, in_memory_repo, sample_question):
        print("\n--- TEST: save_attempt (Mastery Logic) ---")
        in_memory_repo.seed_questions([sample_question])
        user_id = "learner"
        q_id = sample_question.id

        # 1. First Correct Answer
        in_memory_repo.save_attempt(user_id, q_id, is_correct=True)

        # Verify via debug dump (raw state) instead of candidates (business logic)
        rows = in_memory_repo.debug_dump_user_progress(user_id)
        target = next((r for r in rows if r["question_id"] == q_id), None)
        assert target["consecutive_correct"] == 1

        # 2. Second Correct Answer
        in_memory_repo.save_attempt(user_id, q_id, is_correct=True)

        rows = in_memory_repo.debug_dump_user_progress(user_id)
        target = next((r for r in rows if r["question_id"] == q_id), None)
        assert target["consecutive_correct"] == 2

        # 3. Wrong Answer
        in_memory_repo.save_attempt(user_id, q_id, is_correct=False)

        rows = in_memory_repo.debug_dump_user_progress(user_id)
        target = next((r for r in rows if r["question_id"] == q_id), None)
        assert target["consecutive_correct"] == 0

    def test_get_category_stats_aggregates_correctly(self, in_memory_repo):
        print("\n--- TEST: get_category_stats ---")

        # Force threshold to 3 for this test
        with patch("src.config.GameConfig.MASTERY_THRESHOLD", 3):
            q1 = Question(
                id="1",
                text="Q1",
                category="BHP",
                options={},
                correct_option=OptionKey.A,
            )
            q2 = Question(
                id="2",
                text="Q2",
                category="BHP",
                options={},
                correct_option=OptionKey.A,
            )
            q3 = Question(
                id="3",
                text="Q3",
                category="Law",
                options={},
                correct_option=OptionKey.A,
            )

            in_memory_repo.seed_questions([q1, q2, q3])
            user_id = "stats_user"

            # Simulate Mastery for Q1 (3 correct) -> Should be Mastered
            for _ in range(3):
                in_memory_repo.save_attempt(user_id, "1", True)

            # Simulate Seen for Q2 (1 correct) -> Should NOT be Mastered (1 < 3)
            in_memory_repo.save_attempt(user_id, "2", True)

            stats = in_memory_repo.get_category_stats(user_id)
            stats_map = {s["category"]: s for s in stats}

            assert stats_map["BHP"]["total"] == 2
            assert stats_map["BHP"]["mastered"] == 1

            assert stats_map["Law"]["total"] == 1
            assert stats_map["Law"]["mastered"] == 0
