from src.mailer import generate_html_email


def test_generate_html_email_handles_missing_data():
    html = generate_html_email(None)
    assert "No analysis data" in html


def test_generate_html_email_renders_sections():
    payload = {
        "top_themes": [
            {
                "title": "Account Access",
                "description": "Login takes multiple attempts",
                "sentiment": "negative",
                "count": "4",
            }
        ],
        "user_quotes": ["Login fails on first try."],
        "action_ideas": ["Improve retry logic"],
    }

    html = generate_html_email(payload)

    assert "Account Access" in html
    assert "Login fails on first try." in html
    assert "Improve retry logic" in html

