from torch import nn
from ml_training.models.gcn import GraphConvolution, TemporalConvolution


class STGCNBlock(nn.Module):
    """Spatial Temporal Graph Convolution Block.

    Applies spatial graph convolution followed by temporal 1D convolution over frames.
    """

    def __init__(self, in_channels, out_channels, num_nodes=543, stride=1):
        """Initializes the STGCNBlock.

        Args:
            in_channels (int): Number of input channels.
            out_channels (int): Number of output channels.
            num_nodes (int): Number of nodes in the graph (default: 543).
            stride (int): Stride for temporal convolution (default: 1).
        """
        super().__init__()
        # Spatial Graph Convolution
        self.gcn = GraphConvolution(in_channels, out_channels, num_nodes=num_nodes)

        # Temporal 1D Convolution over frames sequence
        self.tcn = TemporalConvolution(out_channels, out_channels, stride=stride)

        # Residual connection
        self.residual = nn.Sequential()
        if in_channels != out_channels or stride != 1:
            self.residual = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=(stride, 1)),
                nn.BatchNorm2d(out_channels)
            )

        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x, adjacency):
        """Forward pass of the STGCNBlock.

        Args:
            x (torch.Tensor): Input tensor of shape (batch_size, in_channels, num_frames, num_nodes).
            adjacency (torch.Tensor): Adjacency matrix of shape (num_nodes, num_nodes) or similar depending on GCN.

        Returns:
            torch.Tensor: Output tensor after applying ST-GCN block.
        """
        bs, in_c, num_frames, num_nodes = x.size()

        # Reshape for spatial graph convolution
        # Combine batches and frames into one batch dimension: (bs * num_frames, num_nodes, in_channels)
        x_gcn_in = x.permute(0, 2, 3, 1).contiguous().view(bs * num_frames, num_nodes, in_c)

        # Apply Graph Convolution
        x_gcn_out = self.gcn(x_gcn_in, adjacency)  # (bs * num_frames, num_nodes, out_channels)

        # Restore original dimension layout: (bs, out_channels, num_frames, num_nodes)
        out_c = x_gcn_out.size(-1)
        x_tcn_in = x_gcn_out.view(bs, num_frames, num_nodes, out_c).permute(0, 3, 1, 2).contiguous()

        # Apply Temporal Convolution
        x_tcn_out = self.tcn(x_tcn_in)

        # Apply residual shortcut
        res = self.residual(x)
        return self.relu(self.bn(x_tcn_out) + res)


class SLGCN(nn.Module):  # pylint: disable=too-many-instance-attributes
    """Skeletal Graph Convolution Network (SL-GCN) for UZSL.

    Consists of stacked Spatial-Temporal GCN blocks and a classification head.
    """

    def __init__(self, in_channels=3, num_classes=100, num_nodes=543):
        """Initializes the SLGCN model.

        Args:
            in_channels (int): Number of input channels (e.g., 3 for x, y, z coordinates).
            num_classes (int): Number of target classes for classification.
            num_nodes (int): Number of nodes in the skeleton graph.
        """
        super().__init__()
        self.num_nodes = num_nodes

        # Initial skeletal node projection (maps coordinate points (x, y, z) to hidden dimensions)
        self.projection = nn.Conv2d(in_channels, 64, kernel_size=1)
        self.bn_proj = nn.BatchNorm2d(64)
        self.relu_proj = nn.ReLU(inplace=True)

        # Stacked Spatial-Temporal Blocks (extract spatio-temporal features)
        self.block1 = STGCNBlock(64, 64, num_nodes=num_nodes)
        self.block2 = STGCNBlock(64, 128, num_nodes=num_nodes, stride=2)  # Temporal downsampling
        self.block3 = STGCNBlock(128, 256, num_nodes=num_nodes, stride=2)

        # Global Pooling and Classifier
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(256, num_classes)

    def forward(self, x, adjacency):
        """Forward pass of the SLGCN model.

        Args:
            x (torch.Tensor): Input tensor of shape (batch_size, in_channels, num_frames, num_nodes).
            adjacency (torch.Tensor): Adjacency matrix for the skeleton graph.

        Returns:
            torch.Tensor: Logits tensor of shape (batch_size, num_classes).
        """
        # Initial projection
        out = self.projection(x)
        out = self.relu_proj(self.bn_proj(out))

        # Apply ST-GCN Blocks
        out = self.block1(out, adjacency)
        out = self.block2(out, adjacency)
        out = self.block3(out, adjacency)

        # Global Average Pooling
        out = self.pool(out)  # Shape: (batch_size, 256, 1, 1)
        out = out.view(out.size(0), -1)  # Flatten to (batch_size, 256)

        # Fully connected layer
        logits = self.fc(out)
        return logits
