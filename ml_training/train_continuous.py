import os
import sys
import math
import json
import glob

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    import torch.nn.functional as F
    from torch.utils.data import Dataset, DataLoader
except ImportError:
    print("⚠️ Ushbu o'qitish skriptini ishlatish uchun PyTorch-ni o'rnating:")
    print("   pip install torch")
    sys.exit(1)

from ml_training.models.continuous_slr import ContinuousSLR

EXPORT_DIR = "../uzsl_bot/exports"
LANDMARKS_DIR = os.path.join(EXPORT_DIR, "landmarks")
NUM_NODES = 543
NUM_FRAMES = 60  # Longer frame sequence for continuous sentences


class UZSLContinuousDataset(Dataset):
    """Custom PyTorch Dataset for Continuous UZSL sentences."""

    def __init__(self, data_dir=LANDMARKS_DIR, target_frames=NUM_FRAMES):
        self.target_frames = target_frames
        self.samples = []
        self.targets = []
        self.target_lengths = []
        self.input_lengths = []
        self.label_map = {}

        # Scan for sentence landmarks or create mock dataset for demonstration if empty
        json_paths = glob.glob(os.path.join(data_dir, "*", "*.json"))

        # Build label map from directory structure
        labels_set = sorted(list(set(os.path.basename(os.path.dirname(p)) for p in json_paths)))
        if not labels_set:
            labels_set = ["salom", "rahmat", "uy", "bormoq", "kelmoq", "yaxshi", "suv", "ichmoq"]
        self.label_map = {lbl: idx for idx, lbl in enumerate(labels_set)}

        if not json_paths:
            print("⚠️ Dataset topilmadi, demo rejimida o'qitish uchun mock ma'lumotlar yaratilmoqda...")
            # Generate mock continuous sequences
            for i in range(10):
                # mock sequence: shape (3, NUM_FRAMES, NUM_NODES)
                self.samples.append(torch.randn(3, target_frames, NUM_NODES))
                # mock sentence labels: sequence of word ids, e.g., "men uy bormoq" -> [0, 2, 3]
                sentence = [i % len(labels_set), (i + 1) % len(labels_set), (i + 2) % len(labels_set)]
                self.targets.append(torch.tensor(sentence, dtype=torch.long))
                self.target_lengths.append(len(sentence))
                self.input_lengths.append(target_frames)
        else:
            for p in json_paths:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)

                frames = data.get("sequence", [])
                if not frames:
                    continue

                # In real scenario, a sentence video would map to multiple words (sequence)
                # For baseline, we mock a sequence of 3 words starting with the folder label
                label_name = os.path.basename(os.path.dirname(p))
                label_idx = self.label_map[label_name]
                sentence = [label_idx, (label_idx + 1) % len(self.label_map), (label_idx + 2) % len(self.label_map)]

                parsed_sequence = self._parse_sequence(frames)
                self.samples.append(parsed_sequence)
                self.targets.append(torch.tensor(sentence, dtype=torch.long))
                self.target_lengths.append(len(sentence))
                self.input_lengths.append(target_frames)

    def _parse_sequence(self, frames):
        seq_len = len(frames)
        tensor_data = torch.zeros(seq_len, NUM_NODES, 3)

        for f_idx, frame in enumerate(frames):
            pose = frame.get("pose", [0.0] * 99)
            face = frame.get("face", [0.0] * 1404)
            lh = frame.get("left_hand", [0.0] * 63)
            rh = frame.get("right_hand", [0.0] * 63)
            all_coords = pose + face + lh + rh

            for node_idx in range(NUM_NODES):
                offset = node_idx * 3
                if offset + 2 < len(all_coords):
                    tensor_data[f_idx, node_idx, 0] = all_coords[offset]
                    tensor_data[f_idx, node_idx, 1] = all_coords[offset + 1]
                    tensor_data[f_idx, node_idx, 2] = all_coords[offset + 2]

        for f_idx in range(seq_len):
            chest_x = (tensor_data[f_idx, 11, 0] + tensor_data[f_idx, 12, 0]) / 2.0
            chest_y = (tensor_data[f_idx, 11, 1] + tensor_data[f_idx, 12, 1]) / 2.0
            chest_z = (tensor_data[f_idx, 11, 2] + tensor_data[f_idx, 12, 2]) / 2.0
            tensor_data[f_idx, :, 0] -= chest_x
            tensor_data[f_idx, :, 1] -= chest_y
            tensor_data[f_idx, :, 2] -= chest_z

        if seq_len == self.target_frames:
            return tensor_data.permute(2, 0, 1)

        interpolated = torch.zeros(self.target_frames, NUM_NODES, 3)
        for i in range(self.target_frames):
            src_idx = (i / (self.target_frames - 1)) * (seq_len - 1) if self.target_frames > 1 else 0
            idx_floor = int(math.floor(src_idx))
            idx_ceil = min(int(math.ceil(src_idx)), seq_len - 1)
            weight = src_idx - idx_floor
            interpolated[i] = (1.0 - weight) * tensor_data[idx_floor] + weight * tensor_data[idx_ceil]

        return interpolated.permute(2, 0, 1)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return (
            self.samples[idx],
            self.targets[idx],
            self.input_lengths[idx],
            self.target_lengths[idx]
        )


def collate_fn(batch):
    """Custom collate function to handle variable length targets for CTC Loss."""
    inputs, targets, input_lengths, target_lengths = zip(*batch)
    inputs = torch.stack(inputs, 0)
    flat_targets = torch.cat(targets, 0)
    return inputs, flat_targets, torch.tensor(input_lengths), torch.tensor(target_lengths)


def train_continuous():
    print("⚙️ UZSL Continuous Machine Learning o'qitish boshlandi...")

    dataset = UZSLContinuousDataset()
    dataloader = DataLoader(dataset, batch_size=2, shuffle=True, collate_fn=collate_fn)
    num_classes = len(dataset.label_map)

    # Initialize model
    model = ContinuousSLR(in_channels=3, num_classes=num_classes, num_nodes=NUM_NODES)

    # CTC Loss: blank token index is num_classes
    criterion = nn.CTCLoss(blank=num_classes, zero_infinity=True)
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"💻 Device: {device}")
    model = model.to(device)

    model.train()
    num_epochs = 5
    print(f"🔥 Continuous Training started for {num_epochs} epochs...")

    for epoch in range(num_epochs):
        epoch_loss = 0.0
        for batch_idx, (inputs, targets, input_lens, target_lens) in enumerate(dataloader):
            inputs = inputs.to(device)
            targets = targets.to(device)

            optimizer.zero_grad()

            # Forward pass: shape (batch_size, num_frames, num_classes + 1)
            outputs = model(inputs)

            # Log softmax over classification classes
            # Permute to (num_frames, batch_size, num_classes + 1) for CTCLoss
            log_probs = F.log_softmax(outputs, dim=-1).permute(1, 0, 2)

            loss = criterion(log_probs, targets, input_lens, target_lens)
            loss.backward()

            # Prevent exploding gradients in LSTM/RNN sequence learning
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=10.0)

            optimizer.step()
            epoch_loss += loss.item()

        avg_loss = epoch_loss / len(dataloader)
        print(f"Epoch [{epoch+1}/{num_epochs}] - Avg CTC Loss: {avg_loss:.4f}")

    # Save model weights
    model_output_path = "uzsl_continuous_model.pt"
    torch.save(model.state_dict(), model_output_path)
    print(f"\n🎉 O'qitish muvaffaqiyatli yakunlandi! Model vaznlari saqlandi: {model_output_path}")


if __name__ == "__main__":
    train_continuous()
