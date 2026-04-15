from __future__ import annotations

import torch
from torch import nn
from torch_geometric.nn import GATConv, GCNConv, SAGEConv


class GNNClassifier(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        output_dim: int = 2,
        model_name: str = "graphsage",
        heads: int = 4,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()
        self.model_name = model_name.lower()
        self.dropout = nn.Dropout(dropout)

        if self.model_name == "gcn":
            self.conv1 = GCNConv(input_dim, hidden_dim)
            self.conv2 = GCNConv(hidden_dim, output_dim)
        elif self.model_name == "gat":
            self.conv1 = GATConv(input_dim, hidden_dim, heads=heads, dropout=dropout)
            self.conv2 = GATConv(hidden_dim * heads, output_dim, heads=1, concat=False, dropout=dropout)
        else:
            self.model_name = "graphsage"
            self.conv1 = SAGEConv(input_dim, hidden_dim)
            self.conv2 = SAGEConv(hidden_dim, output_dim)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        x = self.conv1(x, edge_index)
        x = torch.relu(x)
        x = self.dropout(x)
        x = self.conv2(x, edge_index)
        return x
