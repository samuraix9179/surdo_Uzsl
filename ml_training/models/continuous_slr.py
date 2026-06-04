import torch.nn as nn
from ml_training.models.sstcn import SeparableSTBlock


class ContinuousSLR(nn.Module):
    """Continuous Sign Language Recognition (CSLR) Model.

    Combines Separable Spatial-Temporal Convolutions (SSTCN) as a feature extractor,
    followed by a Bidirectional LSTM (BiLSTM) to model temporal sequence dependencies.
    Outputs classification logits per time step, compatible with CTC Loss.
    """

    def __init__(self, in_channels=3, num_classes=100, num_nodes=543, hidden_dim=256, num_layers=2):
        super(ContinuousSLR, self).__init__()

        # Spatial-Temporal Feature Extractor (reusing SeparableSTBlock)
        self.proj = nn.Sequential(
            nn.Conv2d(in_channels, 64, kernel_size=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True)
        )
        self.block1 = SeparableSTBlock(64, 64)
        self.block2 = SeparableSTBlock(64, 128, stride=1)  # Keep temporal length for continuous alignment
        self.block3 = SeparableSTBlock(128, 256, stride=1)

        # Pooling over spatial nodes dimension (num_nodes = 543)
        # Input to pooling: (batch_size, 256, num_frames, num_nodes)
        # We average over nodes to get: (batch_size, 256, num_frames, 1)
        self.spatial_pool = nn.AdaptiveAvgPool2d((None, 1))

        # Sequence Modeling: BiLSTM
        # Input shape to LSTM: (batch_size, num_frames, input_size)
        self.rnn = nn.LSTM(
            input_size=256,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            bidirectional=True,
            batch_first=True
        )

        # Classification head for CTC (num_classes + 1 for the CTC blank token)
        self.fc = nn.Linear(hidden_dim * 2, num_classes + 1)

    def forward(self, x):
        """Forward pass.

        Input shape: (batch_size, in_channels, num_frames, num_nodes)
        Output shape: (batch_size, num_frames, num_classes + 1)
        """
        # Feature extraction
        out = self.proj(x)            # (bs, 64, num_frames, num_nodes)
        out = self.block1(out)        # (bs, 64, num_frames, num_nodes)
        out = self.block2(out)        # (bs, 128, num_frames, num_nodes)
        out = self.block3(out)        # (bs, 256, num_frames, num_nodes)

        # Pool across nodes (spatial dimension)
        out = self.spatial_pool(out)  # (bs, 256, num_frames, 1)
        out = out.squeeze(-1)         # (bs, 256, num_frames)
        out = out.permute(0, 2, 1)    # (bs, num_frames, 256)

        # Sequence modeling
        out, _ = self.rnn(out)        # (bs, num_frames, hidden_dim * 2)

        # Classification logits per frame
        logits = self.fc(out)         # (bs, num_frames, num_classes + 1)
        return logits
