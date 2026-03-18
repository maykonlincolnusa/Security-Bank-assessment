import responses

from etl.sources.security import fetch_cves


@responses.activate
def test_fetch_cves_maps_payload():
    responses.add(
        responses.GET,
        "https://services.nvd.nist.gov/rest/json/cves/2.0",
        json={
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2026-0001",
                        "published": "2026-03-01T00:00:00.000",
                        "lastModified": "2026-03-02T00:00:00.000",
                        "sourceIdentifier": "nvd@nist.gov",
                        "descriptions": [{"lang": "en", "value": "Example vulnerability"}],
                    }
                }
            ]
        },
        status=200,
    )

    df = fetch_cves("https://services.nvd.nist.gov/rest/json/cves/2.0")

    assert not df.empty
    assert df.loc[0, "cve_id"] == "CVE-2026-0001"
    assert "description" in df.columns
