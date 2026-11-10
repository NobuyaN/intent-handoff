"""Evaluate a checkpoint on a separate directory of held-out trial CSVs."""

import argparse
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from dataset import LABELS, TrajectoryDataset
from model import IntentLSTM


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    if checkpoint["labels"] != list(LABELS):
        raise ValueError("Checkpoint labels do not match dataset labels")
    model = IntentLSTM(**checkpoint["model_config"])
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    data = TrajectoryDataset(args.data_dir, checkpoint["sequence_length"])
    correct = 0
    confusion = torch.zeros(len(LABELS), len(LABELS), dtype=torch.int64)
    with torch.inference_mode():
        for positions, labels in DataLoader(data, batch_size=64):
            predictions = model(positions).argmax(dim=1)
            correct += (predictions == labels).sum().item()
            for actual, predicted in zip(labels.tolist(), predictions.tolist()):
                confusion[actual, predicted] += 1
    print(f"Window accuracy: {correct / len(data):.2%} ({len(data)} windows)")
    print(f"Confusion matrix: rows=actual, columns=predicted; labels={LABELS}")
    print(confusion)


if __name__ == "__main__":
    main()
