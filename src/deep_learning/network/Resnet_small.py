import math
from functools import partial
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchsummary import summary


def get_inplanes():
    return [64,128,256]


def conv3x3x3(in_planes, out_planes, stride=1):
    return nn.Conv3d(in_planes,out_planes,kernel_size=3,stride=stride,padding=1,bias=False)

def conv5x5x5(in_planes,out_planes,stride=1):
    return nn.Conv3d(in_planes,out_planes,kernel_size=5,stride=stride,padding=2,bias=False)

def conv1x1x1(in_planes, out_planes, stride=1):
    return nn.Conv3d(in_planes,out_planes,kernel_size=1,stride=stride,bias=False)


class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, in_planes, planes, stride=1, downsample=None):
        super().__init__()

        self.conv1 = conv3x3x3(in_planes, planes, stride)
        self.bn1 = nn.BatchNorm3d(planes)
        self.dropout1 = nn.Dropout3d(0.3)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3x3(planes, planes)
        self.bn2 = nn.BatchNorm3d(planes)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.dropout1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out


class Resnet_small(nn.Module):

    def __init__(self,block,layer,block_inplanes,n_input_channels=1,conv1_t_size=7,conv1_t_stride=1,no_max_pool=False,shortcut_type='B',widen_factor=1.0,n_classes=512):
        super().__init__()

        block_inplanes = [int(x * widen_factor) for x in block_inplanes]
        
        self.in_planes = block_inplanes[0]
        self.no_max_pool = no_max_pool

        self.conv1 = nn.Conv3d(n_input_channels,self.in_planes,kernel_size=(5, 5, 5),stride=(2, 2, 2),padding=(2, 2, 2),bias=False)
        self.bn1 = nn.BatchNorm3d(self.in_planes)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool3d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(block, block_inplanes[0], layer[0],shortcut_type)
        self.layer2 = self._make_layer(block,block_inplanes[1],layer[1],shortcut_type,stride=2)
        self.layer3 = self._make_layer(block,block_inplanes[2],layer[2],shortcut_type,stride=2)
        
        self.maxpool1 = nn.MaxPool3d(kernel_size=5, stride=1)
        self.avgpool = nn.AvgPool3d(kernel_size=4,stride=1)
        self.fc1 = nn.Linear(1024, n_classes)
        self.fc2 = nn.Linear(n_classes, 128)
        self.fc3 = nn.Linear(128, 64)
        self.fc4 = nn.Linear(64, 1)
        self.convf1 = conv1x1x1(256,1024)
        self.sigmoid = nn.Sigmoid()
        
        
        for m in self.modules():
            if isinstance(m, nn.Conv3d):
                nn.init.kaiming_normal_(m.weight,mode='fan_out',nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm3d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
        
    def _downsample_basic_block(self, x, planes, stride):
        out = F.avg_pool3d(x, kernel_size=1, stride=stride)
        zero_pads = torch.zeros(out.size(0), planes - out.size(1), out.size(2),out.size(3), out.size(4))
        if isinstance(out.data, torch.cuda.FloatTensor):
            zero_pads = zero_pads.cuda()

        out = torch.cat([out.data, zero_pads], dim=1)

        return out

    def _make_layer(self, block, planes, blocks, shortcut_type, stride=1):
        downsample = None
        if stride != 1 or self.in_planes != planes * block.expansion:
            if shortcut_type == 'A':
                downsample = partial(self._downsample_basic_block,planes=planes * block.expansion,stride=stride)
            else:
                downsample = nn.Sequential(conv1x1x1(self.in_planes, planes * block.expansion, stride),nn.BatchNorm3d(planes * block.expansion))

        layers = []
        layers.append(block(in_planes=self.in_planes,planes=planes,stride=stride,downsample=downsample))

        self.in_planes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.in_planes, planes))

        return nn.Sequential(*layers)


    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        if not self.no_max_pool:
            x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        
        
        x = self.maxpool1(x)
        x = self.avgpool(x)
        x = self.convf1(x)
        
        x = x.view(x.size(0), -1)
        
       
        x = self.fc1(x)
        x = self.relu(self.fc2(x))
        x = self.relu(self.fc3(x))
        x = self.sigmoid(self.fc4(x))   
        
        
        return x


def generate_model(**kwargs):
    model = Resnet_small(BasicBlock, [2,2,2], get_inplanes(), **kwargs)
    return model


#For test
if __name__ == '__main__':
    net = generate_model()
    summary(net,(1,128,128,128))