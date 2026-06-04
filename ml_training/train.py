import json
import os
import sys
import glob
import math

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
except ImportError:
    print("⚠️ Ushbu o'qitish skriptini ishlatish uchun PyTorch-ni o'rnating:")
    print("   pip install torch")
    sys.exit(1)

from ml_training.models.sl_gcn import SLGCN
from ml_training.models.sstcn import SSTCN

EXPORT_DIR = "../uzsl_bot/exports"
LANDMARKS_DIR = os.path.join(EXPORT_DIR, "landmarks")
NUM_NODES = 543
NUM_FRAMES = 30  # Fixed sliding window frame length


class UZSLDataset(Dataset):
    """Custom PyTorch Dataset for UZSL skeleton landmarks."""

    def __init__(self, data_dir=LANDMARKS_DIR, target_frames=NUM_FRAMES):
        self.target_frames = target_frames
        self.samples = []
        self.labels = []
        self.label_map = {}

        # Scan for JSON files in label folders
        json_paths = glob.glob(os.path.join(data_dir, "*", "*.json"))
        if not json_paths:
            print(f"⚠️ '{data_dir}' ichida JSON dataset topilmadi.")
            return

        # Build label indices map
        labels_set = sorted(list(set(os.path.basename(os.path.dirname(p)) for p in json_paths)))
        self.label_map = {lbl: idx for idx, lbl in enumerate(labels_set)}

        print(f"📚 Dataset yuklanmoqda: {len(json_paths)} ta namuna, {len(labels_set)} ta sinf.")

        for p in json_paths:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)

            frames = data.get("sequence", [])
            if not frames:
                continue

            label_name = os.path.basename(os.path.dirname(p))
            label_idx = self.label_map[label_name]

            # Parse frames landmarks to tensor: (num_frames, 543, 3)
            parsed_sequence = self._parse_sequence(frames)
            self.samples.append(parsed_sequence)
            self.labels.append(label_idx)

    def _parse_sequence(self, frames):
        """Converts keypoint lists to a normalized, interpolated PyTorch float tensor."""
        seq_len = len(frames)
        tensor_data = torch.zeros(seq_len, NUM_NODES, 3)

        for f_idx, frame in enumerate(frames):
            # Extract flattened (x, y, z) lists
            pose = frame.get("pose", [0.0] * 99)
            face = frame.get("face", [0.0] * 1404)
            lh = frame.get("left_hand", [0.0] * 63)
            rh = frame.get("right_hand", [0.0] * 63)

            # Combine keypoint lists
            all_coords = pose + face + lh + rh

            # Reshape flat coordinates list to (543, 3) keypoints tensor
            for node_idx in range(NUM_NODES):
                offset = node_idx * 3
                if offset + 2 < len(all_coords):
                    tensor_data[f_idx, node_idx, 0] = all_coords[offset]
                    tensor_data[f_idx, node_idx, 1] = all_coords[offset + 1]
                    tensor_data[f_idx, node_idx, 2] = all_coords[offset + 2]

        # Normalize landmarks relative to chest/center origin (pose joint 11, 12 average)
        # Prevents absolute camera placement biases
        for f_idx in range(seq_len):
            chest_x = (tensor_data[f_idx, 11, 0] + tensor_data[f_idx, 12, 0]) / 2.0
            chest_y = (tensor_data[f_idx, 11, 1] + tensor_data[f_idx, 12, 1]) / 2.0
            chest_z = (tensor_data[f_idx, 11, 2] + tensor_data[f_idx, 12, 2]) / 2.0

            tensor_data[f_idx, :, 0] -= chest_x
            tensor_data[f_idx, :, 1] -= chest_y
            tensor_data[f_idx, :, 2] -= chest_z

        # Temporal Interpolation (scale sequences to constant frame length, e.g. 30 frames)
        if seq_len == self.target_frames:
            return tensor_data.permute(2, 0, 1)  # Output: (3, NUM_FRAMES, NUM_NODES)

        interpolated = torch.zeros(self.target_frames, NUM_NODES, 3)
        for i in range(self.target_frames):
            # Map index linearly
            src_idx = (i / (self.target_frames - 1)) * (seq_len - 1) if self.target_frames > 1 else 0
            idx_floor = int(math.floor(src_idx))
            idx_ceil = min(int(math.ceil(src_idx)), seq_len - 1)
            weight = src_idx - idx_floor

            # Linear interpolation between adjacent frames
            interpolated[i] = (1.0 - weight) * tensor_data[idx_floor] + weight * tensor_data[idx_ceil]

        # Shape layout for ST-Conv: (in_channels=3, num_frames=30, num_nodes=543)
        return interpolated.permute(2, 0, 1)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx], self.labels[idx]


def build_default_adjacency_matrix():
    """Generates a default symmetric skeletal adjacency graph matrix for UZSL (543 nodes).

    Defines connection weights between hands joints, face anchors, and pose limbs.
    """
    adj = torch.zeros(NUM_NODES, NUM_NODES)

    # 1. Self loops (Identity)
    for i in range(NUM_NODES):
        adj[i, i] = 1.0

    # 2. Main Pose limb connections (0-32 indices)
    pose_connections = [
        (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),  # upper limbs
        (11, 23), (12, 24), (23, 24),                      # torso
        (23, 25), (25, 27), (24, 26), (26, 28)             # lower limbs
    ]
    for n1, n2 in pose_connections:
        adj[n1, n2] = 1.0
        adj[n2, n1] = 1.0

    # 3. Left Hand Connections (indices 501-521)
    # 4. Right Hand Connections (indices 522-542)
    hand_offsets = [501, 522]
    finger_segments = [
        (0, 1), (1, 2), (2, 3), (3, 4),  # thumb
        (0, 5), (5, 6), (6, 7), (7, 8),  # index
        (5, 9), (9, 10), (10, 11), (11, 12),  # middle
        (9, 13), (13, 14), (14, 15), (15, 16),  # ring
        (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)  # pinky + palm
    ]
    for offset in hand_offsets:
        for n1, n2 in finger_segments:
            idx1 = offset + n1
            idx2 = offset + n2
            if idx1 < NUM_NODES and idx2 < NUM_NODES:
                adj[idx1, idx2] = 1.0
                adj[idx2, idx1] = 1.0

    return adj


def train():
    print("⚙️ UZSL Machine Learning o'qitish boshlandi...")

    # Load dataset
    dataset = UZSLDataset()
    if len(dataset) == 0:
        print("❌ Dataset yuklanmadi. Boshlash uchun avval Telegram bot orqali video yig'ing.")
        return

    dataloader = DataLoader(dataset, batch_size=4, shuffle=True)
    num_classes = len(dataset.label_map)

    # Initialize model: Choose SSTCN (lightweight/mobile optimized) or SLGCN (Graph convolution)
    use_gcn = False  # Choose True to train SL-GCN model
    if use_gcn:
        print("🧬 Architecture Selected: SL-GCN (Graph Convolution)")
        model = SLGCN(in_channels=3, num_classes=num_classes, num_nodes=NUM_NODES)
        adjacency = build_default_adjacency_matrix()
    else:
        print("🧬 Architecture Selected: SSTCN (Separable Spatial-Temporal Conv)")
        model = SSTCN(in_channels=3, num_classes=num_classes, num_nodes=NUM_NODES)
        adjacency = None

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"💻 Device: {device}")
    model = model.to(device)
    if adjacency is not None:
        adjacency = adjacency.to(device)

    # Training Epochs Loop
    model.train()
    num_epochs = 10
    print(f"🔥 Training started for {num_epochs} epochs...")

    for epoch in range(num_epochs):
        epoch_loss = 0.0
        correct = 0
        total = 0

        for batch_idx, (inputs, targets) in enumerate(dataloader):
            inputs = inputs.to(device)
            targets = targets.to(device)

            optimizer.zero_grad()

            if use_gcn:
                outputs = model(inputs, adjacency)
            else:
                outputs = model(inputs)

            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()

        accuracy = 100.0 * correct / total
        avg_loss = epoch_loss / len(dataloader)
        print(f"Epoch [{epoch+1}/{num_epochs}] - Loss: {avg_loss:.4f} - Accuracy: {accuracy:.1f}%")

    # Save model weight parameters
    model_output_path = "uzsl_model.pt"
    torch.save(model.state_dict(), model_output_path)
    print(f"\n🎉 O'qitish muvaffaqiyatli yakunlandi! Model vaznlari saqlandi: {model_output_path}")


if __name__ == "__main__":
    train()
