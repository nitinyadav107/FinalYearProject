# Project Report

## Title

Graph Neural Network Based Network Intrusion Detection System

## Abstract

This project presents an intrusion detection system that models network traffic as a graph and applies Graph Neural Networks to identify suspicious nodes. Each IP address is treated as a node and each communication event forms an edge. By aggregating local traffic features and neighborhood relationships, the model learns patterns that help distinguish benign activity from attack behavior such as DDoS, scanning, and malicious coordination.

## Objectives

- Build a graph from raw traffic flows
- Train a GNN to classify network entities
- Detect malicious or anomalous behavior automatically
- Generate evaluation reports and visual outputs
- Provide a demo-friendly dashboard for presentation

## Modules

1. Data Collection and Preprocessing
2. Graph Construction
3. Feature Engineering
4. GNN Model Training
5. Evaluation and Visualization
6. Inference and Dashboard

## Methodology

1. Load traffic CSV data.
2. Normalize source, destination, bytes, packet, duration, and label fields.
3. Aggregate incoming and outgoing node features.
4. Create graph edges from host communications.
5. Train GCN, GraphSAGE, or GAT for node classification.
6. Evaluate predictions using classification metrics and curves.
7. Rank suspicious nodes based on softmax confidence.

## Software Requirements

- Python 3.10+
- PyTorch
- PyTorch Geometric
- Pandas
- Scikit-learn
- Streamlit

## Expected Output

- Trained model checkpoint
- Confusion matrix
- ROC curve
- Training history plot
- Ranked suspicious hosts
- Dashboard-based demo

## Future Enhancements

- Real-time streaming detection
- Temporal GNNs
- Explainable predictions
- Integration with packet capture tools
- Deployment in enterprise SOC environments
