from unittest.mock import patch

from src.config import Category, GameConfig


class TestCategory:
    def test_all_labels_returns_list(self):
        """Verify all_labels() returns correct category names."""
        labels = Category.all_labels()

        assert isinstance(labels, list)
        assert len(labels) > 0
        # Check for actual label values (not enum member names)
        assert "Bezpieczeństwo i Organizacja Pracy" in labels
        assert "Diagramy Udźwigu i Ładunki" in labels
        assert "Prawo i Dozór Techniczny" in labels

    def test_category_has_required_attributes(self):
        """Each category should have label and icon."""
        for cat in Category:
            assert hasattr(cat, "label")
            assert hasattr(cat, "icon")
            assert isinstance(cat.label, str)
            assert isinstance(cat.icon, str)
            assert len(cat.label) > 0
            assert len(cat.icon) > 0

    def test_get_icon_returns_correct_icon(self):
        """get_icon() should return the correct icon for a given label."""
        icon = Category.get_icon("Bezpieczeństwo i Organizacja Pracy")
        assert icon == "🦺"

        icon = Category.get_icon("Diagramy Udźwigu i Ładunki")
        assert icon == "📦"

    def test_get_icon_returns_default_for_unknown_label(self):
        """get_icon() should return default icon for unknown labels."""
        icon = Category.get_icon("NonExistent Category")
        assert icon == "🔨"  # Default fallback

    def test_all_categories_have_unique_labels(self):
        """Each category should have a unique label."""
        labels = Category.all_labels()
        assert len(labels) == len(set(labels))

    def test_enum_members_match_expected_count(self):
        """Verify we have exactly 6 categories."""
        assert len(Category) == 6


class TestGameConfig:
    def test_mastery_threshold_is_positive(self):
        """MASTERY_THRESHOLD must be >= 1."""
        assert GameConfig.MASTERY_THRESHOLD >= 1

    def test_new_ratio_is_valid_percentage(self):
        """NEW_RATIO must be between 0 and 1."""
        assert 0 <= GameConfig.NEW_RATIO <= 1

    def test_sprint_questions_is_reasonable(self):
        """SPRINT_QUESTIONS should be between 5 and 50."""
        assert 5 <= GameConfig.SPRINT_QUESTIONS <= 50

    def test_passing_score_is_achievable(self):
        """PASSING_SCORE must be <= SPRINT_QUESTIONS."""
        assert GameConfig.PASSING_SCORE <= GameConfig.SPRINT_QUESTIONS

    def test_daily_goal_is_positive(self):
        """DAILY_GOAL must be >= 1."""
        assert GameConfig.DAILY_GOAL >= 1

    def test_categories_matches_enum(self):
        """CATEGORIES list should match Category enum."""
        assert GameConfig.CATEGORIES == Category.all_labels()

    def test_demo_question_ids_is_list(self):
        """DEMO_QUESTION_IDS should be a non-empty list."""
        assert isinstance(GameConfig.DEMO_QUESTION_IDS, list)
        assert len(GameConfig.DEMO_QUESTION_IDS) > 0

    def test_app_title_is_set(self):
        """APP_TITLE should be a non-empty string."""
        assert isinstance(GameConfig.APP_TITLE, str)
        assert len(GameConfig.APP_TITLE) > 0

    def test_app_logo_path_exists(self):
        """APP_LOGO_PATH should be a valid path string."""
        assert isinstance(GameConfig.APP_LOGO_PATH, str)
        assert GameConfig.APP_LOGO_PATH.endswith((".jpg", ".png", ".svg"))

    def test_get_demo_logo_path_returns_default_for_none(self):
        """get_demo_logo_path() should return default when slug is None."""
        path = GameConfig.get_demo_logo_path(None)
        assert path == GameConfig.APP_LOGO_PATH

    def test_get_demo_logo_path_sanitizes_slug(self):
        """get_demo_logo_path() should sanitize prospect slug and check existence."""
        # When file exists, return the custom path
        with patch("src.config.os.path.exists", return_value=True):
            path = GameConfig.get_demo_logo_path("test-company")
            assert path == "assets/logos/test-company.png"

            # Test with special characters (should be removed)
            path = GameConfig.get_demo_logo_path("test@company!")
            assert path == "assets/logos/testcompany.png"

    def test_get_demo_logo_path_falls_back_when_missing(self):
        """get_demo_logo_path() should return default when file doesn't exist."""
        # When file doesn't exist, return default
        with patch("src.config.os.path.exists", return_value=False):
            path = GameConfig.get_demo_logo_path("nonexistent-company")
            assert path == GameConfig.APP_LOGO_PATH

    def test_get_image_base64_handles_urls(self):
        """get_image_base64() should pass through HTTP URLs."""
        url = "https://example.com/image.png"
        result = GameConfig.get_image_base64(url)
        assert result == url

    def test_get_image_base64_returns_fallback_for_missing_file(self):
        """get_image_base64() should return fallback for non-existent files."""
        result = GameConfig.get_image_base64("nonexistent/path.png")
        assert result.startswith("data:image/png;base64,")
        # Should be the 1x1 transparent pixel fallback
        assert "iVBORw0KGgo" in result
