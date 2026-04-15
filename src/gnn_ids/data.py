from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch_geometric.data import Data


CANONICAL_COLUMNS = {
    "src_ip": ["src_ip", "source_ip", "source ip", "src", "source"],
    "dst_ip": ["dst_ip", "destination_ip", "destination ip", "dst", "destination"],
    "bytes": [
        "bytes",
        "total_bytes",
        "flow_bytes",
        "total length of fwd packets",
        "totlen_fwd_pkts",
        "byte_count",
    ],
    "packets": [
        "packets",
        "packet_count",
        "total_packets",
        "total fwd packets",
        "tot_fwd_pkts",
    ],
    "duration": ["duration", "flow duration", "flow_duration"],
    "label": ["label", "attack", "class"],
}

BENIGN_LABELS = {"0", "benign", "normal", "normal traffic", "non-attack", "non attack"}
REQUIRED_COLUMNS = {"src_ip", "dst_ip", "bytes", "packets", "duration", "label"}


@dataclass
class GraphArtifacts:
    data: Data
    node_mapping: dict[str, int]
    scaler: StandardScaler
    feature_columns: list[str]
    normalized_df: pd.DataFrame


def generate_synthetic_flows(output_csv: str | Path, n_flows: int = 1200, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    normal_nodes = [f"10.0.0.{i}" for i in range(1, 31)]
    server_nodes = [f"10.0.1.{i}" for i in range(1, 5)]
    rows = []

    attack_ratio = 0.12
    attacker_count = max(3, int(round(len(normal_nodes) * 0.2)))
    attacker_sources = set(rng.choice(normal_nodes, size=attacker_count, replace=False).tolist())

    for _ in range(n_flows):
        is_attack = int(rng.random() < attack_ratio)
        if is_attack:
            src = rng.choice(sorted(attacker_sources))
            dst = rng.choice(normal_nodes + server_nodes)
            bytes_sent = max(2500, rng.normal(15000, 4200))
            packets = max(24, rng.normal(280, 70))
            duration = max(0.15, rng.normal(1.8, 0.8))
        else:
            normal_pool = [node for node in normal_nodes + server_nodes if node not in attacker_sources]
            if not normal_pool:
                normal_pool = normal_nodes + server_nodes
            src = rng.choice(normal_pool)
            dst = rng.choice(normal_pool)
            bytes_sent = max(120, rng.normal(1400, 450))
            packets = max(2, rng.normal(20, 6))
            duration = max(0.03, rng.normal(0.28, 0.09))

        rows.append(
            {
                "src_ip": src,
                "dst_ip": dst,
                "bytes": float(bytes_sent),
                "packets": float(packets),
                "duration": float(duration),
                "label": is_attack,
            }
        )

    df = pd.DataFrame(rows)
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


def _normalize_name(value: str) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def _infer_column_mapping(columns: Iterable[str]) -> dict[str, str]:
    original_columns = list(columns)
    normalized_lookup = {_normalize_name(column): column for column in original_columns}
    mapping: dict[str, str] = {}

    for canonical_name, candidates in CANONICAL_COLUMNS.items():
        for candidate in candidates:
            normalized_candidate = _normalize_name(candidate)
            if normalized_candidate in normalized_lookup:
                mapping[canonical_name] = normalized_lookup[normalized_candidate]
                break

    missing = REQUIRED_COLUMNS - set(mapping)
    if missing:
        raise ValueError(
            "Could not infer required columns. Missing logical fields: "
            f"{sorted(missing)}. CSV columns were: {original_columns}"
        )
    return mapping


def _normalize_labels(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return series.fillna(0).astype(int).clip(0, 1)

    def map_label(value: object) -> int:
        normalized = _normalize_name(value)
        return 0 if normalized in BENIGN_LABELS else 1

    return series.fillna("benign").map(map_label).astype(int)


def normalize_flows(df: pd.DataFrame) -> pd.DataFrame:
    mapping = _infer_column_mapping(df.columns)
    normalized_df = df.rename(columns={source: target for target, source in mapping.items()}).copy()

    for column in ["bytes", "packets", "duration"]:
        normalized_df[column] = pd.to_numeric(normalized_df[column], errors="coerce").fillna(0.0)

    normalized_df["src_ip"] = normalized_df["src_ip"].astype(str)
    normalized_df["dst_ip"] = normalized_df["dst_ip"].astype(str)
    normalized_df["label"] = _normalize_labels(normalized_df["label"])

    extra_numeric = normalized_df.select_dtypes(include=["number"]).columns.tolist()
    keep_columns = list(REQUIRED_COLUMNS.union(extra_numeric))
    keep_columns = [column for column in normalized_df.columns if column in keep_columns]
    return normalized_df[keep_columns].dropna(subset=["src_ip", "dst_ip"])


def load_flows(csv_path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    return normalize_flows(df)


def _build_node_features(df: pd.DataFrame, feature_columns: Iterable[str] | None = None) -> tuple[pd.DataFrame, list[str]]:
    if feature_columns is None:
        numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()
        feature_columns = [col for col in numeric_columns if col != "label"]
    else:
        feature_columns = list(feature_columns)

    outgoing = df.groupby("src_ip")[feature_columns].agg(["mean", "sum", "count"]).fillna(0.0)
    outgoing.columns = [f"out_{col}_{stat}" for col, stat in outgoing.columns]

    incoming = df.groupby("dst_ip")[feature_columns].agg(["mean", "sum", "count"]).fillna(0.0)
    incoming.columns = [f"in_{col}_{stat}" for col, stat in incoming.columns]

    all_nodes = sorted(set(df["src_ip"]).union(df["dst_ip"]))
    node_features = pd.DataFrame(index=all_nodes)
    node_features = node_features.join(outgoing, how="left").join(incoming, how="left").fillna(0.0)
    return node_features, list(node_features.columns)


def _build_node_labels(df: pd.DataFrame, all_nodes: list[str]) -> np.ndarray:
    # Host-level suspicious labeling: only nodes that appear as malicious sources
    # are marked positive. This keeps destination-only hosts from being mislabeled.
    src_labels = df.groupby("src_ip")["label"].max()
    labels = [int(src_labels.get(node, 0)) for node in all_nodes]
    return np.asarray(labels, dtype=np.int64)


def build_graph_from_flows(
    df: pd.DataFrame,
    test_size: float = 0.2,
    val_size: float = 0.1,
    seed: int = 42,
) -> GraphArtifacts:
    normalized_df = normalize_flows(df)
    node_features, feature_columns = _build_node_features(normalized_df)
    all_nodes = node_features.index.tolist()
    node_mapping = {node: idx for idx, node in enumerate(all_nodes)}
    labels = _build_node_labels(normalized_df, all_nodes)

    edges = normalized_df[["src_ip", "dst_ip"]].drop_duplicates()
    edge_index_np = np.vstack(
        [
            edges["src_ip"].map(node_mapping).to_numpy(),
            edges["dst_ip"].map(node_mapping).to_numpy(),
        ]
    )
    edge_index = torch.tensor(edge_index_np, dtype=torch.long)
    reversed_edge_index = edge_index[[1, 0], :]
    edge_index = torch.cat([edge_index, reversed_edge_index], dim=1)

    scaler = StandardScaler()
    features = scaler.fit_transform(node_features.to_numpy(dtype=np.float32))
    x = torch.tensor(features, dtype=torch.float32)
    y = torch.tensor(labels, dtype=torch.long)

    indices = np.arange(len(all_nodes))
    stratify_labels = labels if len(np.unique(labels)) > 1 else None
    train_idx, test_idx = train_test_split(
        indices,
        test_size=test_size,
        random_state=seed,
        stratify=stratify_labels,
    )

    adjusted_val_size = val_size / (1.0 - test_size)
    train_stratify = labels[train_idx] if len(np.unique(labels[train_idx])) > 1 else None
    train_idx, val_idx = train_test_split(
        train_idx,
        test_size=adjusted_val_size,
        random_state=seed,
        stratify=train_stratify,
    )

    train_mask = torch.zeros(len(all_nodes), dtype=torch.bool)
    val_mask = torch.zeros(len(all_nodes), dtype=torch.bool)
    test_mask = torch.zeros(len(all_nodes), dtype=torch.bool)
    train_mask[train_idx] = True
    val_mask[val_idx] = True
    test_mask[test_idx] = True

    data = Data(
        x=x,
        edge_index=edge_index,
        y=y,
        train_mask=train_mask,
        val_mask=val_mask,
        test_mask=test_mask,
    )
    return GraphArtifacts(
        data=data,
        node_mapping=node_mapping,
        scaler=scaler,
        feature_columns=feature_columns,
        normalized_df=normalized_df,
    )


def build_inference_graph(
    df: pd.DataFrame,
    scaler: StandardScaler | None = None,
) -> tuple[Data, dict[str, int], list[str], pd.DataFrame]:
    normalized_df = normalize_flows(df)
    node_features, feature_columns = _build_node_features(normalized_df)
    all_nodes = node_features.index.tolist()
    node_mapping = {node: idx for idx, node in enumerate(all_nodes)}
    edges = normalized_df[["src_ip", "dst_ip"]].drop_duplicates()
    edge_index_np = np.vstack(
        [
            edges["src_ip"].map(node_mapping).to_numpy(),
            edges["dst_ip"].map(node_mapping).to_numpy(),
        ]
    )
    edge_index = torch.tensor(edge_index_np, dtype=torch.long)
    reversed_edge_index = edge_index[[1, 0], :]
    edge_index = torch.cat([edge_index, reversed_edge_index], dim=1)

    features_np = node_features.to_numpy(dtype=np.float32)
    features = scaler.transform(features_np) if scaler is not None else features_np
    x = torch.tensor(features, dtype=torch.float32)
    data = Data(x=x, edge_index=edge_index)
    return data, node_mapping, feature_columns, normalized_df
