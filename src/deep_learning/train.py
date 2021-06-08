import torch
import torch.nn as nn
import torchvision
from torchvision import transforms
from torch.utils.data import DataLoader
from torch.autograd import Variable
from torch.optim import lr_scheduler
import matplotlib.pyplot as plt
import numpy as np
import sys
import os
import wandb 
import configuration
from network.ResNet import ResNet
from network.VGGNet import VGGNet
from DataLoader import VW_Data
from torchvision import models


def wandb_initiliazer(arguments):
    with wandb.init(project="TUM_DI_Lab", config=arguments):
        config = wandb.config

        model, train_loader, val_loader, loss_fn, optimizer = nn_model(config)

        train(model, train_loader, val_loader, loss_fn, optimizer, config)
    return model


def nn_model(config):
    data_transforms = transforms.Compose([transforms.ToTensor()])

    train_set = VW_Data(data_transforms)
    validation_set = VW_Data(data_transforms)

    # Loading train and validation set
    train_set_loader = DataLoader(train_set, batch_size=config.batch_size, shuffle=False,
                                  num_workers=configuration.training_configuration.number_workers)
    validation_set_loader = DataLoader(validation_set, batch_size=config.batch_size, shuffle=False,
                                       num_workers=configuration.training_configuration.number_workers)

    # Build the model
    net = ResNet.generate_model(config.resnet_depth)
    # net = VGGNet()

    
    #Pretrained models
    net = models.video.r3d_18(pretrained=True)
    net.stem[0] = nn.Sequential(nn.Conv3d(in_channels=1,out_channels=64,kernel_size=(3,7,7),stride=(1,2,2),padding=(1,3,3),bias=False),nn.BatchNorm3d(64),nn.ReLU())
    net.fc = nn.Sequential(nn.Linear(512,128),nn.ReLU(),nn.Linear(128,16),nn.ReLU(),nn.Linear(16,1),nn.Sigmoid())
    
    if configuration.training_configuration.device.type == 'cuda':
        net.cuda()
   
    loss_function = torch.nn.BCELoss()

    optimizer = torch.optim.Adam(net.parameters(), lr=config.lr)
    
    return net, train_set_loader, validation_set_loader, loss_function, optimizer


def validation_phase(NN_model,val_set_loader,loss_function,epoch):
    print("Validating...")
    NN_model.eval()
    
    mini_batches = 0
    loss_val = 0

    for batch_id, (model,label) in enumerate(val_set_loader, 1):

        if configuration.training_configuration.device.type == 'cuda':
            model, label = model.cuda(), label
        else:
            model, label = model, label

        output = NN_model(model)
        loss = loss_function(output, label)

        mini_batches += 1
        loss_val += float(loss)

    loss_val = loss_val/mini_batches
    return loss_val


def train(NN_model, train_set_loader, val_set_loader, loss_function, optimizer, config):
    wandb.watch(NN_model, loss_function, log='all', log_freq=50)

    mini_batches = 0
    loss_value = 0
    all_count = 0
    correct_count = 0

    for epoch in range(config.epochs):
        for batch_id, (model, label) in enumerate(train_set_loader, 1):
            NN_model.train()

            if configuration.training_configuration.device.type == 'cuda':
                model, label = model.cuda(), label
            else:
                model, label = model, label

            output = NN_model(model)
            output = output.to(torch.float32)
            label = label.to(torch.float32)
            if(output == label):
                correct_count += 1
            all_count += 1

            loss = loss_function(output, label)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            mini_batches += 1
            loss_value += float(loss)

            # Plotting in wandb
            if mini_batches % configuration.training_configuration.plot_frequency == 0:
                val_loss = validation_phase(NN_model,val_set_loader,loss_function,epoch)
                training_log(loss_value/configuration.training_configuration.plot_frequency, mini_batches)
                training_log(val_loss,mini_batches,False)

                PATH = "model.pt"
                torch.save({'epoch': epoch, 'model_state_dict': NN_model.state_dict(),
                            'optimizer_state_dict': optimizer.state_dict(), 'loss': loss_value}, PATH)

                loss_value = 0
            accuracy = correct_count / all_count
            
            print('Epoch-{0} lr: {1:f}'.format(epoch, optimizer.param_groups[0]['lr']))
            print("Epoch - {0} accuracy:{1:f}".format(epoch,accuracy))



def training_log(loss, mini_batch, train=True):
    if train:
        wandb.log({'batch': mini_batch, 'loss': loss})
    else:
        wandb.log({'batch': mini_batch, 'loss': loss})
