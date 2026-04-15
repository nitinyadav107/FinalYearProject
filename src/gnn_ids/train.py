from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.metrics import accuracy_score, classification_report, f1_score, precision_score, recall_score

from .artifacts import (
    export_training_history,
    plot_confusion_matrix,
    plot_roc_curve,
    plot_training_curves,
    save_json,
    save_text_report,
)
from .data import build_graph_from_flows, generate_synthetic_flows, load_flows
from .models import GNNClassifier
from .utils import save_metadata, set_seed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a GNN for network intrusion detection.")
    parser.add_argument("--dataset", choices=["synthetic", "csv"], default="synthetic")
    parser.add_argument("--csv-path", default="data/flows.csv")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--lr", type=float, default=0.005)
    parser.add_argument("--weight-decay", type=float, default=5e-4)
    parser.add_argument("--model", choices=["gcn", "graphsage", "gat"], default="graphsage")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--checkpoint", default="models/gnn_ids.pt")
    parser.add_argument("--scaler-path", default="models/scaler.joblib")
    parser.add_argument("--metadata-path", default="models/metadata.json")
    parser.add_argument("--reports-dir", default="reports")
    return parser.parse_args()


def evaluate(model: GNNClassifier, data: torch.Tensor, mask: torch.Tensor) -> tuple[float, float]:
    model.eval()
    with torch.no_grad():
        logits = model(data.x, data.edge_index)
        preds = logits[mask].argmax(dim=1).cpu().numpy()
        labels = data.y[mask].cpu().numpy()
    return accuracy_score(labels, preds), f1_score(labels, preds, zero_division=0)


def main() -> None:
    args = parse_args()
    set_seed(args.seed)

    if args.dataset == "synthetic":
        csv_path = Path("data/synthetic_flows.csv")
        df = generate_synthetic_flows(csv_path, seed=args.seed)
    else:
        df = load_flows(args.csv_path)

    artifacts = build_graph_from_flows(df, seed=args.seed)
    data = artifacts.data

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = GNNClassifier(
        input_dim=data.num_node_features,
        hidden_dim=args.hidden_dim,
        model_name=args.model,
    ).to(device)
    data = data.to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    best_val_f1 = -1.0
    best_state = None
    history: list[dict[str, float]] = []

    for epoch in range(1, args.epochs + 1):
        model.train()
        optimizer.zero_grad()
        logits = model(data.x, data.edge_index)
        loss = F.cross_entropy(logits[data.train_mask], data.y[data.train_mask])
        loss.backward()
        optimizer.step()

        train_acc, train_f1 = evaluate(model, data, data.train_mask)
        val_acc, val_f1 = evaluate(model, data, data.val_mask)
        history.append(
            {
                "epoch": epoch,
                "loss": float(loss.item()),
                "train_acc": float(train_acc),
                "train_f1": float(train_f1),
                "val_acc": float(val_acc),
                "val_f1": float(val_f1),
            }
        )
        print(
            f"Epoch {epoch:02d} | "
            f"loss={loss.item():.4f} | "
            f"train_acc={train_acc:.3f} | train_f1={train_f1:.3f} | "
            f"val_acc={val_acc:.3f} | val_f1={val_f1:.3f}"
        )

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_state = {key: value.detach().cpu() for key, value in model.state_dict().items()}

    if best_state is None:
        raise RuntimeError("Training did not produce a valid model state.")

    model.load_state_dict(best_state)
    model = model.to(device)
    model.eval()

    with torch.no_grad():
        final_logits = model(data.x, data.edge_index)
        test_logits = final_logits[data.test_mask]
        test_preds = test_logits.argmax(dim=1).cpu().numpy()
        test_scores = torch.softmax(test_logits, dim=1)[:, 1].cpu().numpy()
        test_labels = data.y[data.test_mask].cpu().numpy()
        all_scores = torch.softmax(final_logits, dim=1)[:, 1].cpu().numpy()
        all_preds = final_logits.argmax(dim=1).cpu().numpy()

    test_acc = accuracy_score(test_labels, test_preds)
    test_f1 = f1_score(test_labels, test_preds, zero_division=0)
    test_precision = precision_score(test_labels, test_preds, zero_division=0)
    test_recall = recall_score(test_labels, test_preds, zero_division=0)
    report_text = classification_report(test_labels, test_preds, digits=3, zero_division=0)

    print(f"Test accuracy: {test_acc:.3f}")
    print(f"Test F1 score: {test_f1:.3f}")
    print(report_text)

    checkpoint_path = Path(args.checkpoint)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "input_dim": data.num_node_features,
            "hidden_dim": args.hidden_dim,
            "model_name": args.model,
            "feature_columns": artifacts.feature_columns,
            "node_mapping": artifacts.node_mapping,
        },
        checkpoint_path,
    )
    joblib.dump(artifacts.scaler, args.scaler_path)

    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    history_df = export_training_history(history, reports_dir / "training_history.csv")
    plot_training_curves(history_df, reports_dir / "training_curves.png")
    plot_confusion_matrix(test_labels, test_preds, reports_dir / "confusion_matrix.png")
    roc_auc = plot_roc_curve(test_labels, test_scores, reports_dir / "roc_curve.png")
    save_text_report(report_text, reports_dir / "classification_report.txt")

    node_prediction_df = pd.DataFrame(
        {
            "node": list(artifacts.node_mapping.keys()),
            "predicted_label": all_preds,
            "suspicion_score": all_scores,
            "true_label": data.y.cpu().numpy(),
        }
    ).sort_values("suspicion_score", ascending=False)
    node_prediction_df.to_csv(reports_dir / "node_predictions.csv", index=False)

    metrics_payload = {
        "dataset": args.dataset,
        "model": args.model,
        "epochs": args.epochs,
        "test_accuracy": float(test_acc),
        "test_precision": float(test_precision),
        "test_recall": float(test_recall),
        "test_f1": float(test_f1),
        "roc_auc": roc_auc,
        "num_nodes": int(data.num_nodes),
        "num_edges": int(data.num_edges),
    }
    save_json(metrics_payload, reports_dir / "metrics.json")
    save_metadata(args.metadata_path, metrics_payload)

    print(f"Saved checkpoint to {checkpoint_path}")
    print(f"Reports available in {reports_dir.resolve()}")


if __name__ == "__main__":
    main()
