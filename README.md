# GNN-Based Network Intrusion Detection System

This is a complete final-year project implementation for detecting malicious network behavior using Graph Neural Networks (GNNs). It supports both a quick synthetic demo and real CSV traffic datasets such as CICIDS-style exports after column mapping.

## Highlights

- End-to-end graph learning pipeline for intrusion detection
- Flexible CSV preprocessing with automatic column mapping
- Synthetic dataset generator for instant demonstrations
- GNN models: `GCN`, `GraphSAGE`, and `GAT`
- Training pipeline with checkpointing, metrics, plots, and exported reports
- Inference pipeline with suspicious node ranking
- Streamlit dashboard for academic demos and presentations
- Mini project report template with objectives, workflow, and future scope

## Project Structure

```text
finalyearproject/
|-- app.py
|-- data/
|-- models/
|-- reports/
|-- src/gnn_ids/
|   |-- artifacts.py
|   |-- data.py
|   |-- infer.py
|   |-- models.py
|   |-- train.py
|   `-- utils.py
|-- requirements.txt
`-- README.md
```

## Tech Stack

- Python
- PyTorch
- PyTorch Geometric
- Pandas
- Scikit-learn
- Matplotlib
- Seaborn
- Streamlit

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Dataset Format

The pipeline ultimately needs these logical fields:

- `src_ip`
- `dst_ip`
- `bytes`
- `packets`
- `duration`
- `label`

If your CSV uses different names, the project tries to auto-detect them. Typical examples:

- `Source IP` -> `src_ip`
- `Destination IP` -> `dst_ip`
- `Flow Duration` -> `duration`
- `Total Fwd Packets` or `Packet Count` -> `packets`
- `Total Length of Fwd Packets` or `Bytes` -> `bytes`
- `Label` -> `label`

`label` can be numeric (`0` / `1`) or text (`BENIGN`, `DoS`, `PortScan`, etc.). Benign-like labels are mapped to `0`; everything else is mapped to `1`.

## Quick Start

### 1. Train on Synthetic Data

```bash
python -m src.gnn_ids.train --dataset synthetic --epochs 20
```

This creates:

- `data/synthetic_flows.csv`
- `models/gnn_ids.pt`
- `models/scaler.joblib`
- `models/metadata.json`
- `reports/metrics.json`
- `reports/classification_report.txt`
- `reports/node_predictions.csv`
- `reports/training_history.csv`
- plots in `reports/`

### 2. Run Inference

```bash
python -m src.gnn_ids.infer --input data/synthetic_flows.csv --checkpoint models/gnn_ids.pt
```

### 3. Launch Dashboard

```bash
streamlit run app.py
```

## Training With a Real CSV

Place your dataset file in `data/`, then run:

```bash
python -m src.gnn_ids.train --dataset csv --csv-path data/your_dataset.csv --model gat --epochs 30
```

## Workflow

1. Load raw network traffic records from CSV.
2. Normalize column names and labels.
3. Convert communications into a graph.
4. Aggregate node-level behavior features from incoming and outgoing traffic.
5. Train a GNN on node classification.
6. Evaluate using accuracy, precision, recall, F1-score, confusion matrix, and ROC-AUC.
7. Rank suspicious nodes for analyst review.

## Demo Ideas for Viva or Presentation

- Show the generated communication graph statistics.
- Compare `GCN`, `GraphSAGE`, and `GAT`.
- Open the Streamlit dashboard and upload a CSV.
- Explain how GNN captures neighborhood behavior better than normal ML on flat rows.
- Show suspicious nodes with confidence scores from inference output.

## Academic Sections You Can Reuse

### Objective

To design an intelligent intrusion detection system that models network traffic as a graph and uses Graph Neural Networks to identify anomalous or malicious communication patterns.

### Problem Statement

Traditional intrusion detection systems often treat network flows independently and may miss structural attack behavior spread across multiple hosts. This project addresses that limitation by representing communications as graphs and learning relationships between connected entities.

### Future Scope

- Temporal graph modeling for time-aware detection
- Edge classification for malicious flow detection
- Real-time packet capture integration
- Explainable AI for security analysts
- Deployment with SIEM/SOC pipelines

## Notes

- `torch-geometric` may require a compatible local PyTorch installation.
- Synthetic mode is useful when you need a guaranteed demo without downloading public datasets.
- For best academic results, train and compare all three models, then include their metrics table in your report.
