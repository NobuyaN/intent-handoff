"""LSTM classifier: a sequence of XYZ positions -> target-color logits."""

from torch import nn

# x,y,z,joint_1,joint_2,joint_3,joint_4,joint_5,joint_6,joint_7


class IntentLSTM(nn.Module):
    def __init__(self, input_size=3, hidden_size=64, num_layers=1, num_classes=3):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.classifier = nn.Linear(hidden_size, num_classes)

    def forward(self, positions):
        # positions: [batch, sequence_length, 3]. Return raw logits for CE loss.
        _, (hidden, _) = self.lstm(positions)
        return self.classifier(hidden[-1])
