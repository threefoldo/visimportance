'''
    This file contains the data loaders used for the MASSVIS importance model.
    All the required image operations are performed (format conversion, mean substraction, correct channel+dimension formatting)
    For the required data, please see: https://github.com/cvzoya/visimportance/tree/master/data
    
    For MASSVIS training, png images are loaded from massvis/train/ (using the file listing in massvis/train.txt)
    Importance maps (as labels) are loaded as png images from massvis/train_imp/
    
    For MASSVIS validation, png images are loaded from massvis/valid/ (using the file listing in massvis/valid.txt)
    Importance maps (as labels) are loaded as png images from massvis/valid_imp/
    
    Note that maindir is passed during initialization of each data loader to provide the path to the these data directories.
    This gets specified at the top of the train.prototxt and val.prototxt files (see: param_str)
'''

import caffe

import numpy as np
from PIL import Image

import random

###############################################################################
# Massvis Training data loader #
class MassvisTrainDataLayerBubble(caffe.Layer):
    """
        Load (input image, label image) pairs from dataset
        one-at-a-time while reshaping the net to preserve dimensions.
        
        Use this to feed data to a fully convolutional network.
        """
    
    def setup(self, bottom, top):
        """
            Setup data layer according to parameters:
            
            - train_dir: path to training data
            - split: train / val / test
            - mean: tuple of mean values to subtract
            - randomize: load in random order (default: True)
            - seed: seed for randomization (default: None / current time)
            
            example
            
            params = dict(voc_dir="/path/to/data",
            mean=(104.00698793, 116.66876762, 122.67891434),
            split="val")
            """
        # config
        params = eval(self.param_str)
        self.maindir = params['train_dir']
        self.split = params['split']
        self.mean = np.array(params['mean'])
        self.random = params.get('randomize', True)
        self.seed = params.get('seed', None)
        self.binarize = params['binarize']
        
        # two tops: data and label
        if len(top) != 2:
            raise Exception("Need to define two tops: data and label.")
        # data layers have no bottoms
        if len(bottom) != 0:
            raise Exception("Do not define a bottom.")
        
        # load indices for images and labels
        split_f  = '{}/massvis/{}.txt'.format(self.maindir,self.split)
        self.indices = open(split_f, 'r').read().splitlines()
        self.idx = 0
                                              
        # make eval deterministic
        if 'train' not in self.split:
            self.random = False

        # randomization: seed and pick
        if self.random:
            random.seed(self.seed)
            self.idx = random.randint(0, len(self.indices)-1)


    def reshape(self, bottom, top):
        # load image + label image pair
        self.data = self.load_image(self.indices[self.idx])
        self.label = self.load_label(self.indices[self.idx])
        # reshape tops to fit (leading 1 is for batch dimension)
        top[0].reshape(1, *self.data.shape)
        top[1].reshape(1, *self.label.shape)
    
    
    def forward(self, bottom, top):
        # assign output
        top[0].data[...] = self.data
        top[1].data[...] = self.label
        
        # pick next input
        if self.random:
            self.idx = random.randint(0, len(self.indices)-1)
        else:
            self.idx += 1
            if self.idx == len(self.indices):
                self.idx = 0


    def backward(self, top, propagate_down, bottom):
        pass
    
    
    def load_image(self, idx):
        """
            Load input image and preprocess for Caffe:
            - cast to float
            - switch channels RGB -> BGR
            - subtract mean
            - transpose to channel x height x width order
            """
        im = Image.open('{}/massvis/train/{}.png'.format(self.maindir, idx))
        
        in_ = np.array(im, dtype=np.float32)
        
        if len(in_.shape) < 3: # case with black and white images
            w, h = in_.shape
            ret = np.empty((w, h, 3), dtype=np.float32)
            ret[:, :, :] = in_[:, :, np.newaxis]
            in_ = ret
        
        in_ = in_[:,:,::-1]
        in_ -= self.mean
        in_ = in_.transpose((2,0,1))
        return in_
    
    
    def load_label(self, idx):
        """
            Load label image as 1 x height x width integer array of label indices.
            The leading singleton dimension is required by the loss.
            """
        
        im = Image.open('{}/massvis/train_imp/{}.png'.format(self.maindir, idx))
        label = np.array(im, dtype=np.uint8) # values range from 0 to 255
        if self.binarize:
            label = label>255.0*2/3
        else:
            label = label/255.0
        label = label[np.newaxis, ...]
        return label

###############################################################################
# Massvis Validation data loader #
class MassvisDataLayerBubble(caffe.Layer):
    """
    Load (input image, label image) pairs from dataset
    one-at-a-time while reshaping the net to preserve dimensions.

    Use this to feed data to a fully convolutional network.
    """

    def setup(self, bottom, top):
        """
        Setup data layer according to parameters:

        - train_dir: path to training data
        - split: train / val / test
        - mean: tuple of mean values to subtract
        - randomize: load in random order (default: True)
        - seed: seed for randomization (default: None / current time)

        example

        params = dict(voc_dir="/path/to/data",
            mean=(104.00698793, 116.66876762, 122.67891434),
            split="val")
        """
        # config
        params = eval(self.param_str)
        self.maindir = params['val_dir']
        self.split = params['split']
        self.mean = np.array(params['mean'])
        self.random = params.get('randomize', True)
        self.seed = params.get('seed', None)
        self.binarize = params['binarize']

        # two tops: data and label
        if len(top) != 2:
            raise Exception("Need to define two tops: data and label.")
        # data layers have no bottoms
        if len(bottom) != 0:
            raise Exception("Do not define a bottom.")

        # load indices for images and labels
        split_f  = '{}/massvis/{}.txt'.format(self.maindir,
                self.split)
        self.indices = open(split_f, 'r').read().splitlines()
        self.idx = 0

        # make eval deterministic
        if 'train' not in self.split:
            self.random = False

        # randomization: seed and pick
        if self.random:
            random.seed(self.seed)
            self.idx = random.randint(0, len(self.indices)-1)


    def reshape(self, bottom, top):
        # load image + label image pair
        self.data = self.load_image(self.indices[self.idx])
        self.label = self.load_label(self.indices[self.idx])
        # reshape tops to fit (leading 1 is for batch dimension)
        top[0].reshape(1, *self.data.shape)
        top[1].reshape(1, *self.label.shape)


    def forward(self, bottom, top):
        # assign output
        top[0].data[...] = self.data
        top[1].data[...] = self.label

        # pick next input
        if self.random:
            self.idx = random.randint(0, len(self.indices)-1)
        else:
            self.idx += 1
            if self.idx == len(self.indices):
                self.idx = 0


    def backward(self, top, propagate_down, bottom):
        pass


    def load_image(self, idx):
        """
        Load input image and preprocess for Caffe:
        - cast to float
        - switch channels RGB -> BGR
        - subtract mean
        - transpose to channel x height x width order
        """
        im = Image.open('{}/massvis/valid/{}.png'.format(self.maindir, idx))

        in_ = np.array(im, dtype=np.float32) 
        
        if len(in_.shape) < 3: # case with black and white images
            w, h = in_.shape
            ret = np.empty((w, h, 3), dtype=np.float32)
            ret[:, :, :] = in_[:, :, np.newaxis]
            in_ = ret
        # get rid of alpha dimension
        #im.load()
        #if in_.shape[2] == 4:
        #    background = Image.new("RGB", im.size, (255, 255, 255))
        #    background.paste(im, mask=im.split()[3]) # 3 is the alpha channel
        #    in_ = np.array(background, dtype=np.float32)
        
        in_ = in_[:,:,::-1]
        in_ -= self.mean
        in_ = in_.transpose((2,0,1))
        return in_


    def load_label(self, idx):
        """
        Load label image as 1 x height x width integer array of label indices.
        The leading singleton dimension is required by the loss.
        """
    
        im = Image.open('{}/massvis/valid_imp/{}.png'.format(self.maindir, idx)) 
        label = np.array(im, dtype=np.uint8) # values range from 0 to 255
        if self.binarize:
            label = label>255.0*2/3
        else:
            label = label/255.0
        label = label[np.newaxis, ...]
        return label

