from __future__ import annotations

import os

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

DATA_PATH = os.getenv("DEMO_DATA_PATH", "dashboard/data/demo_trust_scores.csv")
EXPLANATION_PATH = os.getenv("DEMO_EXPLANATION_PATH", "dashboard/data/demo_explanations.csv")
API_URL = os.getenv("TRUST_SCORE_URL", "")
API_TOKEN = os.getenv("TRUST_SCORE_TOKEN", "")

st.set_page_config(page_title="Trust Score Dashboard", layout="wide")


@st.cache_data
def load_history() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.sort_values(["institution_id", "date"])


@st.cache_data
def load_explanations() -> pd.DataFrame:
    df = pd.read_csv(EXPLANATION_PATH)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.sort_values(["institution_id", "date", "importance"], ascending=[True, True, False])


def fetch_live_score(institution_id: str):
    if not API_URL or not API_TOKEN:
        return None

    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    url = f"{API_URL.rstrip('/')}/score/{institution_id}"
    try:
        response = httpx.get(url, headers=headers, timeout=10.0)
        if response.status_code != 200:
            return None
        return response.json()
    except Exception:
        return None


def render_alerts(row: pd.Series, score_threshold: float, domain_threshold: float) -> None:
    messages = []
    if float(row["trust_score"]) < score_threshold:
        messages.append(f"Trust score baixo: {row['trust_score']:.2f} < {score_threshold:.2f}")

    for domain in ["finance", "regulatory", "security", "media"]:
        value = float(row[domain])
        if value < domain_threshold:
            messages.append(f"Dominio {domain} abaixo do limite: {value:.2f} < {domain_threshold:.2f}")

    if messages:
        for message in messages:
            st.error(message)
    else:
        st.success("Sem alertas ativos para os thresholds configurados.")


def main() -> None:
    st.title("Trust Score Dashboard (PoC)")
    st.caption("Historico de score, breakdown por dominio, alertas e explicabilidade.")

    history = load_history()
    explanations = load_explanations()

    with st.sidebar:
        st.header("Configuracao")
        institution_id = st.selectbox("Instituicao", sorted(history["institution_id"].unique().tolist()))
        score_threshold = st.slider("Threshold trust score", 0.0, 1.0, 0.65, 0.01)
        domain_threshold = st.slider("Threshold dominios", 0.0, 1.0, 0.60, 0.01)

    hist_inst = history[history["institution_id"] == institution_id].copy()
    exp_inst = explanations[explanations["institution_id"] == institution_id].copy()
    latest = hist_inst.sort_values("date").iloc[-1]

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Trust Score historico")
        fig_score = px.line(hist_inst, x="date", y="trust_score", markers=True)
        fig_score.update_layout(yaxis_range=[0, 1])
        st.plotly_chart(fig_score, use_container_width=True)

    with col2:
        st.subheader("Ultimo snapshot")
        st.metric("Trust Score", f"{latest['trust_score']:.2f}")
        st.metric("Finance", f"{latest['finance']:.2f}")
        st.metric("Regulatory", f"{latest['regulatory']:.2f}")
        st.metric("Security", f"{latest['security']:.2f}")
        st.metric("Media", f"{latest['media']:.2f}")

    st.subheader("Breakdown por dominio")
    domains_df = pd.DataFrame(
        {
            "domain": ["finance", "regulatory", "security", "media"],
            "score": [latest["finance"], latest["regulatory"], latest["security"], latest["media"]],
        }
    )
    fig_domains = px.bar(domains_df, x="domain", y="score", range_y=[0, 1])
    st.plotly_chart(fig_domains, use_container_width=True)

    st.subheader("Alertas automaticos")
    render_alerts(latest, score_threshold=score_threshold, domain_threshold=domain_threshold)

    st.subheader("Explicabilidade (top 10 features)")
    live = fetch_live_score(institution_id)
    if live and live.get("explanation"):
        exp_df = pd.DataFrame(
            {
                "feature": list(live["explanation"].keys()),
                "importance": list(live["explanation"].values()),
            }
        )
        exp_df = exp_df.sort_values("importance", ascending=False).head(10)
        st.caption("Fonte: endpoint /score")
        st.table(exp_df)
    else:
        latest_date = exp_inst["date"].max()
        fallback = exp_inst[exp_inst["date"] == latest_date][["feature", "importance"]].head(10)
        st.caption("Fonte: dataset sintetico de explicabilidade")
        st.table(fallback)

    st.markdown(
        "**Aviso legal/operacional:** este sistema e um **auxilio de decisao**. "
        "Classificacoes com potencial impacto regulatorio exigem revisao humana e, quando necessario, autorizacao legal."
    )


if __name__ == "__main__":
    main()
