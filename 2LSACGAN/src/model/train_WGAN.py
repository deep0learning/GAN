# -*- coding: utf-8 -*-
import os
import sys
import time
import numpy as np
import models_WGAN as models
from keras.utils import generic_utils
# Utils
sys.path.append("../utils")
import general_utils
import data_utils
from data_utils import *
from image_history_buffer import *
import matplotlib.pyplot as plt
from IPython import display
import code
from models_WGAN import *

def classifier_build_test(img_dest_dim,n_classes,generator_model,noise_dim,noise_scale,img_source_dim,opt,X_source_test,Y_source_test,X_dest_test,Y_dest_test,wd=0.0001,pretrained=False):
    classifier = models.vgg16(img_dest_dim,n_classes,pretrained=False,wd=0.0001)
    make_trainable(classifier,False)
    classifier.compile(loss='categorical_crossentropy', optimizer=opt,metrics=['accuracy'])
 
    GenToClassifierModel = models.GenToClassifierModel(generator_model, classifier, noise_dim, img_source_dim)
    GenToClassifierModel.compile(loss='categorical_crossentropy', optimizer=opt,metrics=['accuracy'])

    loss2,acc2 = classifier.evaluate(X_dest_test, Y_dest_test,batch_size=512, verbose=0)                                                                                         
    print('\n Classifier Accuracy on target domain test set after training:  %.2f%%' % (100 * acc2))                                                                             
    loss3, acc3 = classifier.evaluate(X_source_test, Y_source_test,batch_size=512, verbose=0)                                                                                    
    print('\n Classifier Accuracy on source domain test set:  %.2f%%' % (100 * acc3)) 
    evaluating_GENned(noise_scale,noise_dim,X_source_test,Y_source_test,classifier,generator_model)
    return classifier, GenToClassifierModel


def evaluating_GENned(noise_scale,noise_dim,X_source_test,Y_source_test,classifier,gen_model):                                                                               
    #converting source test set into source-GENned set(passing through the GEN)                                                                                              
    n = data_utils.sample_noise(noise_scale, X_source_test.shape[0], noise_dim)                                                                                              
    X_gen_test = gen_model.predict ([n,X_source_test], batch_size=512, verbose=0)                                                                                            
    loss4, acc4 = classifier.evaluate(X_gen_test, Y_source_test,batch_size=256, verbose=0)                                                                                   
    print('\n Classifier Accuracy on source-GENned domain:  %.2f%%' % (100 * acc4))

def train(**kwargs):
    """
    Train standard DCGAN model

    args: **kwargs (dict) keyword arguments that specify the model hyperparameters
    """

    # Roll out the parameters
    generator = kwargs["generator"]
    discriminator = kwargs["discriminator"]
    dset = kwargs["dset"]
    img_dim = kwargs["img_dim"]
    nb_epoch = kwargs["nb_epoch"]
    batch_size = kwargs["batch_size"]
    n_batch_per_epoch = kwargs["n_batch_per_epoch"]
    bn_mode = kwargs["bn_mode"]
    noise_dim = kwargs["noise_dim"]
    noise_scale = kwargs["noise_scale"]
    lr_D = kwargs["lr_D"]
    lr_G = kwargs["lr_G"]
    opt_D = kwargs["opt_D"]
    opt_G = kwargs["opt_G"]
    use_mbd = kwargs["use_mbd"]
    clamp_lower = kwargs["clamp_lower"]
    clamp_upper = kwargs["clamp_upper"]
    image_dim_ordering = kwargs["image_dim_ordering"]
    epoch_size = n_batch_per_epoch * batch_size
    deterministic = kwargs["deterministic"]
    inject_noise = kwargs["inject_noise"]
    model = kwargs["model"]
    no_supertrain = kwargs["no_supertrain"]
    pureGAN = kwargs["pureGAN"]
    lsmooth = kwargs["lsmooth"]
    simple_disc = kwargs["simple_disc"]
    resume = kwargs["resume"]
    name = kwargs["name"]
    wd = kwargs["wd"]
    history_size = kwargs["history_size"]
    monsterClass = kwargs["monsterClass"]
    print("\nExperiment parameters:")
    for key in kwargs.keys():
        print key, kwargs[key]
    print("\n")

    # Setup environment (logging directory etc)
    general_utils.setup_logging("DCGAN")

    # Load and normalize data
    if dset == "mnistM":
        X_source_train,Y_source_train, X_source_test, Y_source_test, n_classes1 = data_utils.load_image_dataset(img_dim, image_dim_ordering,dset='mnist')
        X_dest_train,Y_dest_train, X_dest_test, Y_dest_test, n_classes2 = data_utils.load_image_dataset(img_dim, image_dim_ordering,dset='mnistM')
        #code.interact(local=locals())
    elif dset == "washington_vandal50k":
        X_source_train = data_utils.load_image_dataset(img_dim, image_dim_ordering,dset='washington')
        X_dest_train = data_utils.load_image_dataset(img_dim, image_dim_ordering,dset='vandal50k')
    elif dset == "washington_vandal12classes":
        X_source_train = data_utils.load_image_dataset(img_dim, image_dim_ordering,dset='washington12classes')
        X_dest_train = data_utils.load_image_dataset(img_dim, image_dim_ordering,dset='vandal12classes')
    elif dset == "washington_vandal12classesNoBackground":
        X_source_train,Y_source_train,n_classes1 = data_utils.load_image_dataset(img_dim, image_dim_ordering,dset='washington12classes')
        X_dest_train,Y_dest_train,n_classes2 = data_utils.load_image_dataset(img_dim, image_dim_ordering,dset='vandal12classesNoBackground')
    elif dset == "Wash_Vand_12class_LMDB":
        X_source_train,Y_source_train,n_classes1 = data_utils.load_image_dataset(img_dim, image_dim_ordering,dset='Wash_12class_LMDB')
    elif dset == "OfficeDslrToAmazon":
        X_source_train,Y_source_train,X_source_test, Y_source_test,n_classes1 = data_utils.load_image_dataset(img_dim, image_dim_ordering,dset='OfficeDslr')
        X_dest_train,Y_dest_train,X_dest_test, Y_dest_test, n_classes2 = data_utils.load_image_dataset(img_dim, image_dim_ordering,dset='OfficeAmazon')
    elif dset == "bedrooms":
        X_source_train,Y_source_train,X_source_test, Y_source_test,n_classes1 = data_utils.load_image_dataset(img_dim, image_dim_ordering,dset='bedrooms_small')
        X_dest_train,Y_dest_train,X_dest_test, Y_dest_test, n_classes2 = data_utils.load_image_dataset(img_dim, image_dim_ordering,dset='bedrooms')
    elif dset == "Vand_Vand_12class_LMDB":
        X_source_train,Y_source_train,X_source_test, Y_source_test,n_classes1 = data_utils.load_image_dataset(img_dim, image_dim_ordering,dset='Vand_12class_LMDB_Background')
        X_dest_train,Y_dest_train, X_dest_test, Y_dest_test, n_classes2 = data_utils.load_image_dataset(img_dim, image_dim_ordering,dset='Vand_12class_LMDB')
    else:
        print "dataset not supported"
    if n_classes1 != n_classes2: #sanity check
        print "number of classes mismatch between source and dest domains"
    n_classes = n_classes1 #
    img_source_dim = X_source_train.shape[-3:] # is it backend agnostic?
    img_dest_dim = X_dest_train.shape[-3:] 

    # Create optimizers
    opt_D = data_utils.get_optimizer(opt_D, lr_D)
    opt_G = data_utils.get_optimizer(opt_G, lr_G)
    opt_C = data_utils.get_optimizer('SGD', 0.01)

    #######################
    # Load models
    #######################
    noise_dim = (noise_dim,)
    if generator == "upsampling":
        generator_model = models.generator_upsampling_mnistM(noise_dim, img_source_dim,img_dest_dim, bn_mode,deterministic,pureGAN,inject_noise,wd, dset=dset)
    else:
        generator_model = models.generator_deconv(noise_dim, img_dest_dim, bn_mode, batch_size, dset=dset)

    if simple_disc:
        discriminator_model = models.discriminator_naive(img_dest_dim, bn_mode,model,wd,inject_noise,n_classes,use_mbd)       
        DCGAN_model = models.DCGAN_naive(generator_model, discriminator_model, noise_dim, img_source_dim)
    elif discriminator == "disc_resnet":
        discriminator_model = models.discriminatorResNet(img_dest_dim, bn_mode,model,wd,monsterClass,inject_noise,n_classes,use_mbd)       
        DCGAN_model = models.DCGAN(generator_model, discriminator_model, noise_dim, img_source_dim, img_dest_dim,monsterClass)
    else:
        discriminator_model = models.disc1(img_dest_dim, bn_mode,model,wd,monsterClass,inject_noise,n_classes,use_mbd)
        DCGAN_model = models.DCGAN(generator_model, discriminator_model, noise_dim, img_source_dim, img_dest_dim,monsterClass)

    ####special options for bedrooms dataset:
    if dset == "bedrooms":
        generator_model = models.generator_dcgan(noise_dim, img_source_dim,img_dest_dim, bn_mode,deterministic,pureGAN,inject_noise,wd)
        discriminator_model = models.discriminator_naive(img_dest_dim, bn_mode,model,wd,inject_noise,n_classes,use_mbd,model_name="discriminator_naive")       
        DCGAN_model = models.DCGAN_naive(generator_model, discriminator_model, noise_dim, img_source_dim)

    ############################
    # Compile models
    ############################
    generator_model.compile(loss='mse', optimizer=opt_G)

    models.make_trainable(discriminator_model, False)
    #discriminator_model.trainable = False
    if model == 'wgan':
        DCGAN_model.compile(loss=models.wasserstein, optimizer=opt_G)
        models.make_trainable(discriminator_model, True)
        discriminator_model.compile(loss=models.wasserstein, optimizer=opt_D)
    if model == 'lsgan':
        if simple_disc:
            DCGAN_model.compile(loss=['mse'], optimizer=opt_G)
            models.make_trainable(discriminator_model, True)
            discriminator_model.compile(loss=['mse'], optimizer=opt_D)
        elif monsterClass:
            DCGAN_model.compile(loss=['categorical_crossentropy'], optimizer=opt_G)
            models.make_trainable(discriminator_model, True)
            discriminator_model.compile(loss=['categorical_crossentropy'], optimizer=opt_D)
        else:
            DCGAN_model.compile(loss=['mse','categorical_crossentropy'], loss_weights=[1.0, 1.0], optimizer=opt_G)
            models.make_trainable(discriminator_model, True)
            discriminator_model.compile(loss=['mse','categorical_crossentropy'], loss_weights=[1.0, 1.0], optimizer=opt_D)

    visualize = True
        
    if resume: ########loading previous saved model weights
        data_utils.load_model_weights(generator_model, discriminator_model, DCGAN_model, name)

    #####################
    ###classifier
    #####################
    if not( (dset == 'mnistM') or (dset == 'bedrooms') ):
        classifier, GenToClassifierModel = classifier_build_test(img_dest_dim,n_classes,generator_model,noise_dim,noise_scale,img_source_dim,opt_C,X_source_test,Y_source_test,X_dest_test,Y_dest_test,wd=0.0001)

  
    gen_iterations = 0
    max_history_size = int( history_size * batch_size) 
    img_buffer = ImageHistoryBuffer((0,)+img_source_dim, max_history_size, batch_size, n_classes)
    #################
    # Start training
    ################
    for e in range(nb_epoch):
        # Initialize progbar and batch counter
        progbar = generic_utils.Progbar(epoch_size)
        batch_counter = 1
        start = time.time()

        while batch_counter < n_batch_per_epoch:
            if no_supertrain is None:
                if (gen_iterations < 25) and (not resume):
                    disc_iterations = 100
                if gen_iterations % 500 == 0:
                    disc_iterations = 10
                else:
                    disc_iterations = kwargs["disc_iterations"]
            else:
                if (gen_iterations <25) and (not resume):
                    disc_iterations = 100
                else:
                    disc_iterations = kwargs["disc_iterations"]

            ###################################
            # 1) Train the critic / discriminator
            ###################################
            list_disc_loss_real = []
            list_disc_loss_gen = []
            list_gen_loss = []
   
            for disc_it in range(disc_iterations):

                # Clip discriminator weights
                #for l in discriminator_model.layers:
                #    weights = l.get_weights()
                #    weights = [np.clip(w, clamp_lower, clamp_upper) for w in weights]
                #    l.set_weights(weights)

                X_dest_batch, Y_dest_batch,idx_dest_batch = next(data_utils.gen_batch(X_dest_train, Y_dest_train, batch_size))
                X_source_batch, Y_source_batch,idx_source_batch = next(data_utils.gen_batch(X_source_train, Y_source_train, batch_size))

                # Create a batch to feed the discriminator model
                X_disc_real, X_disc_gen = data_utils.get_disc_batch(X_dest_batch, generator_model, batch_counter, batch_size, noise_dim, X_source_batch, noise_scale=noise_scale)
                if model == 'wgan':
                # Update the discriminator
                    current_labels_real = -np.ones(X_disc_real.shape[0]) 
                    current_labels_gen = np.ones(X_disc_gen.shape[0]) 
                if model == 'lsgan':
                    if simple_disc: #for real domain I put [labels 0 0 0...0], for fake domain I put [0 0...0 labels]
                        current_labels_real = np.ones(X_disc_real.shape[0]) 
                        #current_labels_gen = -np.ones(X_disc_gen.shape[0]) 
                        current_labels_gen = np.zeros(X_disc_gen.shape[0]) 
                    elif monsterClass: #for real domain I put [labels 0 0 0...0], for fake domain I put [0 0...0 labels]
                        current_labels_real= np.concatenate((Y_dest_batch,np.zeros((X_disc_real.shape[0],n_classes))),axis=1)
                        current_labels_gen= np.concatenate((np.zeros((X_disc_real.shape[0],n_classes)),Y_source_batch),axis=1)
                    else:
                        current_labels_real = [np.ones(X_disc_real.shape[0]),Y_dest_batch] 
                        Y_fake_batch =(1.0/n_classes)*np.ones([X_disc_gen.shape[0],n_classes]) 
                        current_labels_gen =[np.zeros(X_disc_gen.shape[0]), Y_fake_batch ]
                #label smoothing
                #current_labels_real = np.multiply(current_labels_real, lsmooth) #usually lsmooth = 0.7
                disc_loss_real = discriminator_model.train_on_batch(X_disc_real, current_labels_real)
                img_buffer.add_to_buffer(X_disc_gen,current_labels_gen, batch_size)
                bufferImages, bufferLabels = img_buffer.get_from_buffer(batch_size)
                disc_loss_gen = discriminator_model.train_on_batch(bufferImages, bufferLabels)

                list_disc_loss_real.append(disc_loss_real)
                list_disc_loss_gen.append(disc_loss_gen)

            #######################
            # 2) Train the generator
            #######################
            X_gen = data_utils.sample_noise(noise_scale, batch_size, noise_dim)
            X_source_batch2, Y_source_batch2,idx_source_batch2 = next(data_utils.gen_batch(X_source_train, Y_source_train, batch_size))
#            w1 = classifier.get_weights() #FOR DEBUG
            if model == 'wgan':
                gen_loss = DCGAN_model.train_on_batch([X_gen,X_source_batch2], -np.ones(X_gen.shape[0]))
            if model == 'lsgan':
                if simple_disc: 
                    gen_loss =  DCGAN_model.train_on_batch([X_gen,X_source_batch2], np.ones(X_gen.shape[0])) #TRYING SAME BATCH OF DISC?
                elif monsterClass: 
                    labels_gen= np.concatenate((Y_source_batch2,np.zeros((X_disc_real.shape[0],n_classes))),axis=1)
                    gen_loss = DCGAN_model.train_on_batch([X_gen,X_source_batch2], labels_gen)
                else:
                    gen_loss = DCGAN_model.train_on_batch([X_gen,X_source_batch2], [np.ones(X_gen.shape[0]),Y_source_batch2])
#            gen_loss2 = GenToClassifierModel.train_on_batch([X_gen,X_source_batch2], Y_source_batch2) 

#            w2 = classifier.get_weights() #FOR DEBUG
 #           for a,b in zip(w1, w2):
  #              if np.all(a == b):
   #                 print "no bug in GEN model update"
    #            else:
     #               print "BUG IN GEN MODEL UPDATE"
            list_gen_loss.append(gen_loss)

            gen_iterations += 1
            batch_counter += 1

            progbar.add(batch_size, values=[("Loss_D", 0.5*np.mean(list_disc_loss_real) + 0.5*np.mean(list_disc_loss_gen)),
                                            ("Loss_D_real", np.mean(list_disc_loss_real)),
                                            ("Loss_D_gen", np.mean(list_disc_loss_gen)),
                                            ("Loss_G", np.mean(list_gen_loss))])

            # plot images 1 times per epoch
            if batch_counter % (n_batch_per_epoch) == 0:
                X_source_batch_plot,Y_source_batch_plot,idx_source_plot = next(data_utils.gen_batch(X_source_test,Y_source_test, batch_size=32))
                data_utils.plot_generated_batch(X_dest_test,X_source_test, generator_model,noise_dim, image_dim_ordering,idx_source_plot,batch_size=32)
            if gen_iterations % (n_batch_per_epoch*5) == 0:
                if visualize:
                    BIG_ASS_VISUALIZATION_slerp(X_source_train[1], generator_model, noise_dim)

        print ("Dest labels:") 
        print (Y_dest_test[idx_source_plot].argmax(1))
        print ("Source labels:") 
        print (Y_source_batch_plot.argmax(1))
        print('\nEpoch %s/%s, Time: %s' % (e + 1, nb_epoch, time.time() - start))

        # Save model weights (by default, every 5 epochs)
        data_utils.save_model_weights(generator_model, discriminator_model, DCGAN_model, e, name)
#        loss2,acc2 = classifier.evaluate(X_dest_test, Y_dest_test,batch_size=512, verbose=0)                                                                                         
#        print('\n Classifier Accuracy on target domain test set after training:  %.2f%%' % (100 * acc2))                                                                             
#        loss3, acc3 = classifier.evaluate(X_source_test, Y_source_test,batch_size=512, verbose=0)                                                                                    
#        print('\n Classifier Accuracy on source domain test set:  %.2f%%' % (100 * acc3)) 
#        evaluating_GENned(noise_scale,noise_dim,X_source_test,Y_source_test,classifier,generator_model)


