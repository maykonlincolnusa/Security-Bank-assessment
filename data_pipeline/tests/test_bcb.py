import pandas as pd
import responses

from etl.sources.bcb import fetch_bcb_series


@responses.activate
def test_fetch_bcb_series_parses_data():
    responses.add(
        responses.GET,
        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados",
        match=[
            responses.matchers.query_param_matcher(
                {"formato": "json", "dataInicial": "01/01/2024", "dataFinal": "31/01/2024"}
            )
        ],
        json=[{"data": "01/01/2024", "valor": "123.45"}],
        status=200,
    )

    df = fetch_bcb_series("1", start_date="2024-01-01", end_date="2024-01-31")

    assert not df.empty
    assert df.loc[0, "series_id"] == "1"
    assert pd.api.types.is_datetime64_any_dtype(df["ref_date"])
    assert df.loc[0, "value"] == 123.45
