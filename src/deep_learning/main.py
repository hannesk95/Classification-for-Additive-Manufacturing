import sys

import torch

sys.path.append(".")   #TODO Ugly - currently needed for LRZ AI System - find better solution
sys.path.append("..")
sys.path.append("../..")

import logging
import mlflow.pytorch
import pytorch_lightning as pl

from torchvision.transforms import transforms
from torch.utils.data import DataLoader, random_split

from src.deep_learning.AMCDataset import AMCDataset
from src.deep_learning.ParamConfigurator import ParamConfigurator
from src.deep_learning.ClassificationTask import ClassificationTask
from src.deep_learning.ArchitectureSelector import ArchitectureSelector


def main():
    # 1. Define configuration parameters
    config = ParamConfigurator()

    # 2. Select neural network architecture and create model
    selector = ArchitectureSelector(config.architecture_type, config)
    nn_model = selector.select_architecture()

    # 3. Define transformations
    transformations = transforms.Compose([transforms.ToTensor()])

    # 4. Initialize dataset
    # train_dataset = AMCDataset(config.train_data_dir, transform=transformations)
    # validation_dataset = AMCDataset(config.validation_data_dir, transform=transformations)
    dataset = AMCDataset(config, transform=transformations)

    # 5 Split dataset into train and val set
    torch.manual_seed(42)
    train_dataset, validation_dataset = random_split(dataset,
                                                     [int(config.data_len*config.train_split),
                                                      config.data_len - int(config.data_len*config.train_split)])

    # 5. Create dataloader
    train_data_loader = DataLoader(train_dataset, batch_size=config.batch_size, shuffle=True, **config.kwargs)
    validation_data_loader = DataLoader(validation_dataset, batch_size=config.batch_size, shuffle=False, **config.kwargs)

    # 6. Start MLflow logging
    mlflow.set_tracking_uri(config.mlflow_log_dir)
    mlflow.set_experiment(config.experiment_name)
    mlflow.pytorch.autolog()

    # 7. Create classifier
    classifier = ClassificationTask(nn_model=nn_model, config=config)

    # 8. Start training
    trainer = pl.Trainer(max_epochs=config.num_epochs, accelerator='horovod', gpus=1,
                         precision=16)  # , accumulate_grad_batches=10)
    # trainer = pl.Trainer(max_epochs=config.num_epochs)
    trainer.fit(classifier, train_data_loader, validation_data_loader)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.DEBUG)
    logging.info('Started main_deep_learning')

    main()

    logging.info('Finished main_deep_learning')
