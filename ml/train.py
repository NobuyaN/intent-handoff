"""Train on logger CSVs. Use a separate directory of trials for evaluation."""

import argparse
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader

from dataset import LABELS, TrajectoryDataset
from model import IntentLSTM


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data")
    parser.add_argument("--output", type=Path, default=Path("checkpoints/intent_lstm.pt"))
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--sequence-length", type=int, default=40)
    parser.add_argument("--stride", type=int, default=10)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error("--epochs must be positive")

    torch.manual_seed(42)
    data = TrajectoryDataset(args.data_dir, args.sequence_length, args.stride)
    present = {label for _, label in data}
    if len(present) != len(LABELS):
        print("Warning: missing target classes; this run only verifies the training pipeline.")
    loader = DataLoader(data, batch_size=args.batch_size, shuffle=True)
    model = IntentLSTM(hidden_size=args.hidden_size)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    criterion = nn.CrossEntropyLoss()

    model.train()
    for epoch in range(args.epochs):
        total_loss = 0.0
        for positions, labels in loader:
            optimizer.zero_grad()
            loss = criterion(model(positions), labels)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_loss += loss.item() * len(labels)
        print(f"Epoch {epoch + 1:03d}: loss={total_loss / len(data):.4f}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "model_state": model.state_dict(),
        "model_config": {"hidden_size": args.hidden_size},
        "sequence_length": args.sequence_length,
        "labels": list(LABELS),
        "preprocessing": "subtract_first_position",
    }, args.output)
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
