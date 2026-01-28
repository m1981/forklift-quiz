# tests/unit/components/test_mobile_dashboard.py

from unittest.mock import MagicMock, patch

from src.components.mobile.dashboard import mobile_dashboard


def test_mobile_dashboard_renders_all_categories():
    """
    GIVEN a list of categories
    WHEN mobile_dashboard is called
    THEN it should call the underlying custom component with correct data.
    """
    categories = [
        {"id": "A", "label": "Cat A", "icon": "A", "progress": 0.1},
    ]

    # Patch the INTERNAL component function, not 'st'
    with patch(
        "src.components.mobile.dashboard._mobile_dashboard_component"
    ) as mock_comp:
        # Setup the mock to return a dummy object with an 'action' attribute
        mock_result = MagicMock()
        mock_result.action = None  # Simulate no click
        mock_comp.return_value = mock_result

        # Act
        mobile_dashboard(categories)

        # Assert
        mock_comp.assert_called_once()
        # Check that data passed to component matches input
        call_kwargs = mock_comp.call_args.kwargs
        assert call_kwargs["data"]["categories"] == categories


def test_mobile_dashboard_handles_click_event():
    """
    GIVEN the custom component returns an action
    WHEN mobile_dashboard runs
    THEN it should return the correct dictionary.
    """
    categories = []

    with patch(
        "src.components.mobile.dashboard._mobile_dashboard_component"
    ) as mock_comp:
        # Setup Mock: Simulate the JS component returning an action
        mock_result = MagicMock()
        # The component returns an object where .action is a dict
        mock_result.action = {"type": "SPRINT", "payload": None}
        mock_comp.return_value = mock_result

        # Act
        result = mobile_dashboard(categories)

        # Assert
        assert result == {"type": "SPRINT", "payload": None}
