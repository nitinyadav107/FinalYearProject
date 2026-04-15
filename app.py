from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.gnn_ids.data import generate_synthetic_flows, normalize_flows
from src.gnn_ids.infer import run_inference


st.set_page_config(page_title="GNN IDS Dashboard", layout="wide")


def read_json(path: str | Path) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_preview(csv_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw_df = pd.read_csv(csv_path)
    normalized_df = normalize_flows(raw_df)
    return raw_df, normalized_df


def model_artifacts_ready() -> tuple[bool, list[str]]:
    required_files = [
        Path("models/gnn_ids.pt"),
        Path("models/scaler.joblib"),
    ]
    missing = [str(path) for path in required_files if not path.exists()]
    return len(missing) == 0, missing


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


st.title("GNN-Based Network Intrusion Detection")
st.caption("Interactive demo dashboard for final-year project presentation")

left, right = st.columns([1.1, 0.9])

with left:
    st.subheader("Project Overview")
    st.write(
        "This system converts network communications into a graph where IP addresses become nodes "
        "and connections become edges. A Graph Neural Network then predicts which nodes show suspicious behavior."
    )
    st.markdown(
        """
        **Detectable patterns**

        - DDoS-style abnormal request bursts
        - Port scanning behavior
        - Botnet-like coordination
        - Malicious hosts with unusual neighborhood activity
        """
    )

with right:
    st.subheader("Saved Training Metrics")
    metrics = read_json("reports/metrics.json")
    ready, missing_artifacts = model_artifacts_ready()
    if ready:
        st.success("Deployment model artifacts are available")
    else:
        st.warning(f"Missing model artifacts: {', '.join(missing_artifacts)}")
    if metrics:
        metric_cols = st.columns(4)
        metric_cols[0].metric("Accuracy", f"{metrics.get('test_accuracy', 0):.3f}")
        metric_cols[1].metric("Precision", f"{metrics.get('test_precision', 0):.3f}")
        metric_cols[2].metric("Recall", f"{metrics.get('test_recall', 0):.3f}")
        metric_cols[3].metric("F1", f"{metrics.get('test_f1', 0):.3f}")
        st.write(metrics)
    else:
        st.info("Train the model first to populate metrics.")

st.divider()

tab_demo, tab_dataset, tab_infer = st.tabs(["Synthetic Demo", "Dataset Preview", "Inference"])

with tab_demo:
    st.subheader("Generate Synthetic Demo Data")
    flow_count = st.slider("Number of flows", min_value=300, max_value=5000, value=1200, step=100)
    seed = st.number_input("Random seed", min_value=1, max_value=9999, value=42)
    if st.button("Generate synthetic CSV"):
        df = generate_synthetic_flows("data/synthetic_flows.csv", n_flows=flow_count, seed=int(seed))
        st.session_state["synthetic_demo_df"] = df
        st.success(f"Generated {len(df)} flows at data/synthetic_flows.csv")
        st.dataframe(df.head(15), use_container_width=True)

    synthetic_demo_df = st.session_state.get("synthetic_demo_df")
    if isinstance(synthetic_demo_df, pd.DataFrame) and not synthetic_demo_df.empty:
        st.download_button(
            label="Download complete synthetic CSV",
            data=dataframe_to_csv_bytes(synthetic_demo_df),
            file_name="synthetic_flows.csv",
            mime="text/csv",
        )

with tab_dataset:
    st.subheader("Preview Dataset")
    input_choice = st.radio("Choose input source", ["Existing file", "Upload CSV"], horizontal=True)

    csv_path: Path | None = None
    if input_choice == "Existing file":
        default_path = st.text_input("CSV path", value="data/synthetic_flows.csv")
        csv_path = Path(default_path)
    else:
        uploaded = st.file_uploader("Upload a traffic CSV", type=["csv"])
        if uploaded is not None:
            csv_path = Path("data/uploaded_preview.csv")
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            csv_path.write_bytes(uploaded.getvalue())

    if csv_path and csv_path.exists():
        try:
            raw_df, normalized_df = load_preview(csv_path)
            st.write("Raw columns:", list(raw_df.columns))
            summary_cols = st.columns(4)
            summary_cols[0].metric("Flows", len(normalized_df))
            summary_cols[1].metric("Unique Sources", normalized_df["src_ip"].nunique())
            summary_cols[2].metric("Unique Destinations", normalized_df["dst_ip"].nunique())
            summary_cols[3].metric("Attack Ratio", f"{normalized_df['label'].mean():.2%}")
            st.write("Normalized preview")
            st.dataframe(normalized_df.head(20), use_container_width=True)
        except Exception as exc:
            st.error(str(exc))
    else:
        st.info("Choose a CSV file to inspect its normalized format.")

with tab_infer:
    st.subheader("Run Saved Model on a CSV")
    inference_path = st.text_input("Inference CSV path", value="data/synthetic_flows.csv")
    checkpoint_path = st.text_input("Checkpoint path", value="models/gnn_ids.pt")
    scaler_path = st.text_input("Scaler path", value="models/scaler.joblib")

    if st.button("Run inference"):
        try:
            results = run_inference(inference_path, checkpoint_path, scaler_path)
            st.session_state["inference_results_df"] = results
            st.success("Inference completed")
            st.dataframe(results.head(25), use_container_width=True)
            st.bar_chart(results.head(10).set_index("node")["suspicion_score"])
        except Exception as exc:
            st.error(str(exc))

    inference_results_df = st.session_state.get("inference_results_df")
    if isinstance(inference_results_df, pd.DataFrame) and not inference_results_df.empty:
        st.download_button(
            label="Download complete inference CSV",
            data=dataframe_to_csv_bytes(inference_results_df),
            file_name="inference_results.csv",
            mime="text/csv",
        )

st.divider()

st.subheader("Generated Visuals")
visual_cols = st.columns(3)
for index, asset in enumerate(
    ["reports/training_curves.png", "reports/confusion_matrix.png", "reports/roc_curve.png"]
):
    asset_path = Path(asset)
    if asset_path.exists():
        visual_cols[index].image(str(asset_path), caption=asset_path.name, use_container_width=True)
    else:
        visual_cols[index].info(f"{asset_path.name} will appear after training.")
