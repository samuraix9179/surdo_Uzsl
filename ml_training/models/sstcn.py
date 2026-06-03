import torch
import torch.nn as nn


class SeparableSTBlock(nn.Module):
    """Decomposed Spatial-Temporal Convolution block.

    Separates spatial channel mixing from temporal feature tracking.
    """

    def __init__(self, in_channels, out_channels, stride=1):
        super(SeparableSTBlock, self).__init__()

        # Spatial Depthwise Convolution (mixes landmark point coordinates locally)
        self.spatial_conv = nn.Conv2d(
            in_channels,
            in_channels,
            kernel_size=(1, 3),
            padding=(0, 1),
            groups=in_channels
        )

        # Temporal Pointwise Convolution (mixes channel filters across frames)
        self.temporal_conv = nn.Conv2d(
            in_channels,
            out_channels,
            kernel_size=(9, 1),
            stride=(stride, 1),
            padding=(4, 0)
        )

        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)

        # Skip residual shortcut
        self.shortcut = nn.Sequential()
        if in_channels != out_channels or stride != 1:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=(stride, 1)),
                nn.BatchNorm2d(out_channels)
            )

    def forward(self, x):
        """Input shape: (batch_size, in_channels, num_frames, num_nodes)"""
        out = self.spatial_conv(x)
        out = self.temporal_conv(out)
        out = self.bn(out)
        return self.relu(out + self.shortcut(x))


class SSTCN(nn.Module):
    """Separable Spatial-Temporal Convolution Network (SSTCN) for UZSL.

    A highly optimized, lightweight model ideal for fast TFLite mobile GPU inference.
    """

    def __init__(self, in_channels=3, num_classes=100, num_nodes=543):
        super(SSTCN, self).__init__()
        self.num_nodes = num_nodes

        # Initial Feature Projector
        self.proj = nn.Sequential(
            nn.Conv2d(in_channels, 64, kernel_size=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True)
        )

        # Stacked Separable ST Blocks
        self.block1 = SeparableSTBlock(64, 64)
        self.block2 = SeparableSTBlock(64, 128, stride=2)
        self.block3 = SeparableSTBlock(128, 256, stride=2)

        # Global average pool and classification logits
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(256, num_classes)

    def forward(self, x):
        """Input shape: (batch_size, in_channels, num_frames, num_nodes)

        Returns: (batch_size, num_classes) probabilities.
        """
        out = self.proj(x)
        out = self.block1(out)
        out = self.block2(out)
        out = self.block3(out)

        out = self.pool(out)
        out = out.view(out.size(0), -1)  # Flatten to (batch_size, 256)
        logits = self.fc(out)
        return logits
