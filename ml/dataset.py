"""Read fixed-length windows from the trajectory logger's CSV files."""

import csv
import math
from pathlib import Path

import torch
from torch.utils.data import Dataset

LABELS = ("red", "green", "blue")


class TrajectoryDataset(Dataset):
    def __init__(self, data_dir, sequence_length=40, stride=10):
        if sequence_length < 1 or stride < 1:
            raise ValueError("sequence_length and stride must be positive")
        self.samples = []
        for path in sorted(Path(data_dir).glob("trial_*.csv")):
            parts = path.stem.split("_")
            if len(parts) < 3 or parts[2] not in LABELS:
                raise ValueError(f"Unknown target label in {path}")
            with path.open(newline="") as stream:
                positions = [
                    [float(row[key]) for key in ("x", "y", "z")]
                    for row in csv.DictReader(stream)
                ]
            if not all(math.isfinite(v) for row in positions for v in row):
                raise ValueError(f"Non-finite position in {path}")
            label = LABELS.index(parts[2])
            for start in range(0, len(positions) - sequence_length + 1, stride):
                window = torch.tensor(
                    positions[start:start + sequence_length], dtype=torch.float32
                )
                # Relative positions remove dependence on the starting location.
                self.samples.append((window - window[0], label))
        if not self.samples:
            raise ValueError(f"No windows found in {data_dir}; check CSVs and sequence length")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        return self.samples[index]
