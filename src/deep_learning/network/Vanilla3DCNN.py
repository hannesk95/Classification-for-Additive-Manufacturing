import torch
import torch.nn as nn
import torch.nn.functional as F
import pytorch_lightning as pl
from torchsummary import summary
import numpy as np
from sklearn.metrics import accuracy_score


class Vanilla3DCNN(pl.LightningModule):
    """#TODO: Add docstring."""

    def __init__(self):
        """#TODO: Add docstring."""

        super(Vanilla3DCNN, self).__init__()

        self.conv1 = nn.Conv3d(in_channels=1, out_channels=32, kernel_size=(9, 9, 9))
        self.conv2 = nn.Conv3d(in_channels=32, out_channels=64, kernel_size=(7, 7, 7))
        self.conv3 = nn.Conv3d(in_channels=64, out_channels=96, kernel_size=(5, 5, 5))
        self.conv4 = nn.Conv3d(in_channels=96, out_channels=128, kernel_size=(3, 3, 3))

        self.fc1 = nn.Linear(in_features=128, out_features=32)
        self.fc2 = nn.Linear(in_features=32, out_features=1)

        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(p=0.2)
        self.max_pool3d = nn.MaxPool3d(kernel_size=(2, 2, 2), stride=2)
        self.avg_pool3d = nn.AvgPool3d(kernel_size=(2, 2, 2), stride=1)
        self.global_pool3d = nn.MaxPool3d(kernel_size=(11, 11, 11))

    def forward(self, x):
        """#TODO: Add docstring."""

        # Convolution block 1
        x = self.conv1(x)
        x = self.relu(x)

        # Convolution block 2
        x = self.conv2(x)
        x = self.relu(x)
        x = self.max_pool3d(x)

        # Convolution block 3
        x = self.conv3(x)
        x = self.relu(x)
        x = self.max_pool3d(x)

        # Convolution block 4
        x = self.conv4(x)
        x = self.relu(x)
        x = self.max_pool3d(x)

        # Transition block to fully connected layers
        x = self.avg_pool3d(x)
        x = self.global_pool3d(x)
        x = x.view(x.size(0), -1)
        x = self.dropout(x)

        # Classification block (fully connected)
        x = self.fc1(x)
        x = self.relu(x)
        x = self.dropout(x)
        x = self.fc2(x)
        x = torch.sigmoid(x)

        return x

    def general_step(self, batch, batch_idx, mode):
        model, label = batch
        prediction = self.forward(model)
        loss = F.binary_cross_entropy(prediction, label)
        acc = accuracy_score(label.detach().numpy(), prediction.round().detach().numpy())

        return loss, acc

    def general_end(self, outputs, mode):
        # average over all batches aggregated during one epoch
        avg_loss = torch.stack([x[mode + '_loss'] for x in outputs]).mean()
        avg_acc = torch.stack([x[mode + '_acc'] for x in outputs]).mean()
        return avg_loss, avg_acc

    def training_step(self, batch, batch_idx):
        loss, acc = self.general_step(batch, batch_idx, "train")
        self.log('train_loss', loss, on_step=True, on_epoch=True, prog_bar=True, logger=True)
        self.log('train_acc', acc, on_step=True, on_epoch=True, prog_bar=True, logger=True)
        return {'loss': loss, 'acc': acc}

    def validation_step(self, batch, batch_idx):
        loss, acc = self.general_step(batch, batch_idx, "val")
        self.log('val_loss', loss, on_step=True, on_epoch=True, prog_bar=True, logger=True)
        self.log('val_acc', acc, on_step=True, on_epoch=True, prog_bar=True, logger=True)
        return {'val_loss': loss, 'val_acc': acc}

    def validation_end(self, outputs):
        avg_loss, avg_acc = self.general_end(outputs, "val")
        return {'val_loss': avg_loss, 'avg_acc': avg_acc}

    def configure_optimizers(self): # TODO pass optimizer here
        return torch.optim.Adam(self.parameters(), lr=0.02)

    def get_progress_bar_dict(self):
        tqdm_dict = super().get_progress_bar_dict()
        if 'v_num' in tqdm_dict:
            del tqdm_dict['v_num']
        return tqdm_dict


# For testing purposes
if __name__ == '__main__':
    model = Vanilla3DCNN()

    if torch.cuda.device_count() > 0:
        summary(model.cuda(), (1, 128, 128, 128))
    else:
        summary(model, (1, 128, 128, 128))
