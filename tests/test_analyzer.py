from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd

from src.analyzer import analyze_reviews


def test_analyze_reviews_returns_none_for_empty_dataframe():
    empty = pd.DataFrame()
    assert analyze_reviews(empty) is None


@patch("google.generativeai.GenerativeModel")
def test_analyze_reviews_parses_json_response(mock_model):
    mock_response = MagicMock()
    mock_response.text = """
    {
        "top_themes": [{"title": "Latency", "description": "Slow loads", "sentiment": "negative", "count": "3"}],
        "user_quotes": ["App is slow"],
        "action_ideas": ["Optimize API calls"]
    }
    """

    mock_instance = MagicMock()
    mock_instance.generate_content.return_value = mock_response
    mock_model.return_value = mock_instance

    df = pd.DataFrame(
        [
            {
                "date": datetime(2025, 12, 1),
                "source": "Google Play",
                "rating": 3,
                "text": "Loads slowly",
            }
        ]
    )

    result = analyze_reviews(df)

    assert result["top_themes"][0]["title"] == "Latency"
    mock_instance.generate_content.assert_called_once()

