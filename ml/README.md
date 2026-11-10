# LSTM intent baseline

Predict red, green, or blue from XYZ trajectory windows. Input is
`[batch, sequence_length, 3]`; output is three logits. Each window is translated
relative to its first position. Defaults use 40 samples (about two seconds at
the logger's nominal 20 Hz) with a stride of 10. Short trials are skipped.
Timestamps are not used or resampled; this assumes roughly uniform sampling.

Run from the repository root:

```sh
python -m pip install -r ml/requirements.txt
python ml/train.py --data-dir data --epochs 20
python ml/evaluate.py --checkpoint checkpoints/intent_lstm.pt --data-dir data_test
```

Put held-out trials in `data_test/`, with the same `trial_ID_COLOR_TIMESTAMP.csv`
filenames and `time_s,x,y,z` columns produced by the logger. Split whole trials
before windowing: overlapping windows from one trial must not appear in both
training and evaluation. The scripts do not automatically split your files.

Only one blue trial currently exists, so training on the supplied data is a
pipeline smoke test. Collect multiple independent trials for every color before
assessing prediction quality. Accuracy is per window, not per trial. With
randomized target layouts, XYZ alone may not generalize to color; target
positions would need to become additional inputs in a later model.

This starter runs on CPU and saves weights, model settings, label order, and
preprocessing information. It is offline code; ROS inference and handoff are
not connected. `baseline.py` and `generate_data.py` remain placeholders.

LSTM API reference: https://docs.pytorch.org/docs/stable/generated/torch.nn.LSTM.html
