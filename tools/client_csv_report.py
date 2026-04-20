from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

# Allow running from anywhere while still importing `src.*`
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.gnn_ids.data import CANONICAL_COLUMNS, normalize_flows  # noqa: E402
from src.gnn_ids.infer import run_inference  # noqa: E402


def _has_any_label_column(columns: list[str]) -> bool:
    existing = {str(c).strip().lower() for c in columns}
    for candidate in CANONICAL_COLUMNS["label"]:
        if str(candidate).strip().lower() in existing:
            return True
    return False


def build_report(
    *,
    csv_path: Path,
    checkpoint: str,
    scaler_path: str,
    threshold: float,
    out_dir: Path,
) -> dict:
    raw_df = pd.read_csv(csv_path)
    if not _has_any_label_column(list(raw_df.columns)):
        # Client datasets often won't have ground-truth labels; add a benign label column
        # so the pipeline can normalize columns and build features.
        raw_df["label"] = 0

    normalized_df = normalize_flows(raw_df)

    results = run_inference(str(csv_path), checkpoint, scaler_path, threshold=threshold)
    source_nodes = set(normalized_df["src_ip"].astype(str).tolist())

    suspicious_nodes = results.loc[results["predicted_label"] == 1, ["node", "suspicion_score"]].copy()
    suspicious_source_nodes = results.loc[
        results["node"].isin(source_nodes) & (results["predicted_label"] == 1),
        ["node", "suspicion_score"],
    ].copy()

    suspicious_source_set = set(suspicious_source_nodes["node"].astype(str).tolist())
    suspicious_comm_mask = normalized_df["src_ip"].astype(str).isin(suspicious_source_set)
    suspicious_communications = normalized_df.loc[suspicious_comm_mask].copy()

    out_dir.mkdir(parents=True, exist_ok=True)
    results.to_csv(out_dir / "inference_results.csv", index=False)
    suspicious_source_nodes.sort_values("suspicion_score", ascending=False).to_csv(
        out_dir / "suspicious_source_nodes.csv", index=False
    )
    suspicious_nodes.sort_values("suspicion_score", ascending=False).to_csv(
        out_dir / "suspicious_nodes.csv", index=False
    )
    suspicious_communications.to_csv(out_dir / "suspicious_communications.csv", index=False)

    payload = {
        "input_csv": str(csv_path),
        "threshold": float(threshold),
        "total_flows": int(len(normalized_df)),
        "total_unique_sources": int(normalized_df["src_ip"].nunique()),
        "total_unique_nodes": int(
            len(set(normalized_df["src_ip"].astype(str)).union(set(normalized_df["dst_ip"].astype(str))))
        ),
        "suspicious_nodes_count": int(len(suspicious_nodes)),
        "suspicious_source_ips_count": int(len(suspicious_source_nodes)),
        "suspicious_communications_count": int(len(suspicious_communications)),
        "outputs": {
            "inference_results_csv": str((out_dir / "inference_results.csv").resolve()),
            "suspicious_nodes_csv": str((out_dir / "suspicious_nodes.csv").resolve()),
            "suspicious_source_nodes_csv": str((out_dir / "suspicious_source_nodes.csv").resolve()),
            "suspicious_communications_csv": str((out_dir / "suspicious_communications.csv").resolve()),
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a simple suspicious-IP report from a client CSV.")
    parser.add_argument("--csv", required=True, help="Path to client CSV file (flows).")
    parser.add_argument("--checkpoint", default="models/gnn_ids.pt")
    parser.add_argument("--scaler", default="models/scaler.joblib")
    parser.add_argument("--threshold", type=float, default=0.75)
    parser.add_argument("--outdir", default="reports/client_run")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_report(
        csv_path=Path(args.csv),
        checkpoint=args.checkpoint,
        scaler_path=args.scaler,
        threshold=args.threshold,
        out_dir=Path(args.outdir),
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

