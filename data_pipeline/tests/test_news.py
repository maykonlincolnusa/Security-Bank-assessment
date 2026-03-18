import responses

from etl.sources.news import fetch_news
from etl.utils import simple_sentiment


def test_simple_sentiment_scoring():
    text = "Banco reporta lucro solido, sem risco de fraude"
    assert simple_sentiment(text) > 0


@responses.activate
def test_fetch_news_adds_sentiment():
    responses.add(
        responses.GET,
        "https://gnews.io/api/v4/search",
        match=[
            responses.matchers.query_param_matcher(
                {"q": "banco", "language": "pt", "token": "token"}
            )
        ],
        json={
            "articles": [
                {"title": "Banco em crescimento", "description": "Lucro solido"},
                {"title": "Ataque e vazamento", "description": "Alerta regulatorio"},
            ]
        },
        status=200,
    )

    df = fetch_news("https://gnews.io/api/v4/search", "token", "banco")
    assert "sentiment_score" in df.columns
    assert df.shape[0] == 2
