import math
import torch
import torch.nn as nn


class GraphConvolution(nn.Module):  # type: ignore[misc]
    """Spatial Graph Convolution Layer for skeleton keypoints.

    Applies spatial graph convolution based on adjacency matrix:
    Y = D^(-1/2) * A_sym * D^(-1/2) * X * W

    Attributes:
        in_channels (int): Number of channels in the input graph.
        out_channels (int): Number of channels in the output graph.
        num_nodes (int): Number of nodes in the graph.
        weight (nn.Parameter): Learnable weight matrix.
        edge_importance (nn.Parameter): Learnable adjacency weight multiplier.
    """

    def __init__(self, in_channels: int, out_channels: int, num_nodes: int = 543) -> None:
        """Initializes the Graph Convolution Layer.

        Args:
            in_channels (int): Number of channels in the input graph.
            out_channels (int): Number of channels in the output graph.
            num_nodes (int, optional): Number of nodes in the graph. Defaults to 543.
        """
        super(GraphConvolution, self).__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.num_nodes = num_nodes

        # Learnable weight matrix
        self.weight = nn.Parameter(torch.FloatTensor(in_channels, out_channels))
        # Learnable adjacency weight multiplier (to let the model optimize graph connections)
        self.edge_importance = nn.Parameter(torch.ones(num_nodes, num_nodes))

        self.reset_parameters()

    def reset_parameters(self) -> None:
        """Resets the learnable parameters of the layer."""
        nn.init.kaiming_uniform_(self.weight, a=math.sqrt(5) if hasattr(self, 'math') else 1e-2)

    def forward(self, x: torch.Tensor, adjacency: torch.Tensor) -> torch.Tensor:
        """Forward pass for the Spatial Graph Convolution Layer.

        Args:
            x (torch.Tensor): Input tensor of shape (batch_size, num_nodes, in_channels).
            adjacency (torch.Tensor): Adjacency matrix tensor of shape (num_nodes, num_nodes).

        Returns:
            torch.Tensor: Output tensor of shape (batch_size, num_nodes, out_channels).
        """
        # Apply edge importance weights to adjacency
        a_weighted = adjacency * self.edge_importance

        # Compute degree matrix and symmetric normalization: D^(-1/2) * A * D^(-1/2)
        row_sum = torch.sum(a_weighted, dim=1)
        row_sum_inv_sqrt = torch.pow(row_sum, -0.5)
        row_sum_inv_sqrt[torch.isinf(row_sum_inv_sqrt)] = 0.0
        d_inv_sqrt = torch.diag(row_sum_inv_sqrt)

        a_normalized = torch.matmul(torch.matmul(d_inv_sqrt, a_weighted), d_inv_sqrt)

        # Graph convolution: A_norm * X
        # x is (bs, num_nodes, in_channels) -> reshape for batched matrix multiplication
        x_g = torch.matmul(a_normalized.unsqueeze(0), x)  # Shape: (bs, num_nodes, in_channels)

        # Linear transform: X * W
        out = torch.matmul(x_g, self.weight)  # Shape: (bs, num_nodes, out_channels)
        return out


class TemporalConvolution(nn.Module):  # type: ignore[misc]
    """1D Temporal Convolution Layer over the frames sequence.

    Attributes:
        conv (nn.Conv2d): 2D Convolution layer applied over the temporal dimension.
        bn (nn.BatchNorm2d): Batch normalization layer.
        relu (nn.ReLU): ReLU activation function.
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int = 9,
        stride: int = 1,
        padding: int = 4
    ) -> None:
        """Initializes the Temporal Convolution Layer.

        Args:
            in_channels (int): Number of channels in the input tensor.
            out_channels (int): Number of channels produced by the convolution.
            kernel_size (int, optional): Size of the convolving kernel. Defaults to 9.
            stride (int, optional): Stride of the convolution. Defaults to 1.
            padding (int, optional): Zero-padding added to both sides of the input. Defaults to 4.
        """
        super(TemporalConvolution, self).__init__()
        self.conv = nn.Conv2d(
            in_channels,
            out_channels,
            kernel_size=(kernel_size, 1),
            stride=(stride, 1),
            padding=(padding, 0)
        )
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass for the Temporal Convolution Layer.

        Args:
            x (torch.Tensor): Input tensor of shape (batch_size, in_channels, num_frames, num_nodes).

        Returns:
            torch.Tensor: Output tensor of shape (batch_size, out_channels, num_frames, num_nodes).
        """
        out = self.conv(x)
        out = self.bn(out)
        return self.relu(out)
