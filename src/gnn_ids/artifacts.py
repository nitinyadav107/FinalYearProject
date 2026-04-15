from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.metrics import ConfusionMatrixDisplay, RocCurveDisplay, confusion_matrix, roc_auc_score


def export_training_history(history: list[dict[str, float]], output_csv: str | Path) -> pd.DataFrame:
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    history_df = pd.DataFrame(history)
    history_df.to_csv(output_path, index=False)
    return history_df


def plot_training_curves(history_df: pd.DataFrame, output_path: str | Path) -> None:
    sns.set_theme(style="whitegrid")
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    axes[0].plot(history_df["epoch"], history_df["loss"], label="Loss", color="#c0392b")
    axes[0].set_title("Training Loss")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")

    axes[1].plot(history_df["epoch"], history_df["train_f1"], label="Train F1", color="#2980b9")
    axes[1].plot(history_df["epoch"], history_df["val_f1"], label="Validation F1", color="#27ae60")
    axes[1].set_title("F1 Score by Epoch")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("F1 Score")
    axes[1].legend()

    figure.tight_layout()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def plot_confusion_matrix(y_true, y_pred, output_path: str | Path) -> None:
    figure, axis = plt.subplots(figsize=(5, 4))
    labels = [0, 1]
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    display = ConfusionMatrixDisplay(confusion_matrix=matrix, display_labels=["Normal", "Attack"])
    display.plot(ax=axis, colorbar=False)
    axis.set_title("Confusion Matrix")
    figure.tight_layout()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def plot_roc_curve(y_true, y_score, output_path: str | Path) -> float | None:
    if len(set(y_true)) < 2:
        return None

    figure, axis = plt.subplots(figsize=(5, 4))
    RocCurveDisplay.from_predictions(y_true, y_score, ax=axis)
    axis.set_title("ROC Curve")
    figure.tight_layout()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return float(roc_auc_score(y_true, y_score))


def save_text_report(report_text: str, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_text, encoding="utf-8")


def save_json(payload: dict, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
