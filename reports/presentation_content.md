# GNN IDS Presentation Outline

## Slide 1: Title

- Graph Neural Network Based Network Intrusion Detection System
- Final Year Project Presentation
- Purpose: Detect malicious network behavior automatically

## Slide 2: Problem Statement

- Modern networks contain many connected devices and huge traffic volume
- Traditional detection often inspects single rows of data independently
- Multi-host attacks like botnets, scans, and coordinated abuse are structural
- Security teams need faster automated detection with less manual effort

## Slide 3: Project Overview

- This project converts network traffic into a graph
- IP addresses or hosts become nodes
- Communications between them become edges
- A GNN learns node behavior using both local features and neighbor activity

## Slide 4: Real Problem Solved

- Detects DDoS-like communication bursts
- Flags suspicious scanning behavior
- Identifies malicious or infected hosts
- Supports anomaly-focused investigation and faster SOC triage

## Slide 5: Why GNN

- Normal neural networks work well on fixed grids or sequences
- Network traffic is relational and graph-shaped
- GNN uses neighborhood context, not just individual flow features
- This makes it more suitable for connected attack patterns

## Slide 6: System Workflow

1. Collect traffic data
2. Normalize CSV fields
3. Build graph from source-destination communication
4. Aggregate node features
5. Train GCN, GraphSAGE, or GAT
6. Evaluate metrics and generate reports
7. Run inference to rank suspicious nodes

## Slide 7: Dataset Used

- Synthetic dataset for guaranteed demo and testing
- Real CSV support for CICIDS-style traffic exports
- Required logical fields:
  - src_ip
  - dst_ip
  - bytes
  - packets
  - duration
  - label
- Text labels like BENIGN are converted to 0, attacks to 1

## Slide 8: Technology Stack

- Python for implementation
- PyTorch and PyTorch Geometric for GNN training
- Pandas and scikit-learn for preprocessing and metrics
- Matplotlib and Seaborn for visualization
- Streamlit for interactive dashboard

## Slide 9: Models and Their Roles

- GCN: strong baseline graph convolution model
- GraphSAGE: scalable neighborhood aggregation
- GAT: attention-based graph learning
- Training exports checkpoint, reports, and graphs

## Slide 10: Results

- Use generated metrics from the tested synthetic run
- Show training curve
- Mention accuracy, precision, recall, and F1 score

## Slide 11: Visual Outputs

- Confusion matrix
- ROC curve
- Suspicious node ranking
- Dashboard for dataset preview and live inference

## Slide 12: Conclusion

- Graph-based learning improves security analysis for connected systems
- The project provides an end-to-end prototype from data to dashboard
- It can be extended to real-time pipelines and temporal GNNs
