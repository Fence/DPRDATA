# coding:utf-8
import os
import time
import pickle
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
plt.switch_backend('agg') # do not require GUI


class QuitProgram(Exception):
    def __init__(self, message='Quit the program.\n'):
        Exception.__init__(self, message)
        self.message = message
        

def print_args(args, output_file=''):
    """
    Print all arguments of an argparse instance
    """
    print('\n Arguments:')
    for k, v in sorted(args.__dict__.items(), key=lambda x:x[0]):
        print('{}: {}'.format(k, v))
    if output_file:
        output_file.write('\n Arguments:\n')
        for k, v in sorted(args.__dict__.items(), key=lambda x:x[0]):
            output_file.write('{}: {}\n'.format(k, v))
        output_file.write('\n')


def pos_tagging(agent_mode, domain):
    import ipdb
    from tqdm import tqdm
    from nltk.tag import StanfordPOSTagger
    pos_model = '/home/fengwf/stanford/postagger/models/english-bidirectional-distsim.tagger'
    pos_jar = '/home/fengwf/stanford/postagger/stanford-postagger.jar'
    pos_tagger = StanfordPOSTagger(pos_model, pos_jar)
    
    if agent_mode == 'act':
        indata = pickle.load(open('data/%s_labeled_text_data.pkl' % domain, 'r'))
    else:
        _, __, indata = pickle.load(open('data/refined_%s_data.pkl' % domain, 'r'))
    if domain == 'wikihow':
        indata = indata[: 150]

    ipdb.set_trace()
    # pos_data = []
    pos_data = load_pkl('data/%s_%s_pos.pkl' % (domain, agent_mode))
    try:
        for i in range(118, len(indata)):
            pos_text = []
            for j in range(len(indata[i])):
                print('Text %d/%d Sent %d/%d' % (i+1, len(indata), j+1, len(indata[i])))
                if len(indata[i][j]) == 0:
                    continue
                last_sent = [w.lower() for w in indata[i][j]['last_sent']]
                this_sent = [w.lower() for w in indata[i][j]['this_sent']]
                pos_sent = [pos_tagger.tag(last_sent), pos_tagger.tag(this_sent)]
                pos_text.append(pos_sent)
            pos_data.append(pos_text)
    except:
        print('Error! i=%d, j=%d' % (i, j))
    save_pkl(pos_data, 'data/%s_%s_pos.pkl' % (domain, agent_mode))




def conv2d(x, output_dim, kernel_size, stride, initializer, activation_fn=tf.nn.relu, padding='VALID', name='conv2d'):
    with tf.variable_scope(name):
        # data_format = 'NHWC'
        stride = [1, stride[0], stride[1], 1]
        kernel_size = [kernel_size[0], kernel_size[1], x.get_shape()[-1], output_dim]
        
        w = tf.get_variable('w', kernel_size, tf.float32, initializer=initializer)
        conv = tf.nn.conv2d(x, w, stride, padding)

        b = tf.get_variable('b', [output_dim], initializer=tf.constant_initializer(0.1))
        out = tf.nn.bias_add(conv, b)

    if activation_fn != None:
        out = activation_fn(out)
    return out, w, b


def max_pooling(x, kernel_size, stride, padding='VALID', name='max_pool'):
    with tf.variable_scope(name):
        stride = [1, stride[0], stride[1], 1]
        kernel_size = [1, kernel_size[0], kernel_size[1], 1]
        return tf.nn.max_pool(x, kernel_size, stride, padding)


def linear(x, output_dim, activation_fn=None, name='linear'):
    with tf.variable_scope(name):
        w = tf.get_variable('w', [x.get_shape()[1], output_dim], tf.float32, 
            initializer=tf.truncated_normal_initializer(0, 0.1))
        b = tf.get_variable('b', [output_dim], initializer=tf.constant_initializer(0.1))
        out = tf.nn.bias_add(tf.matmul(x, w), b)

    if activation_fn != None:
        out = activation_fn(out)
    return out, w, b


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")


def plot_results(results, domain, filename):
    print('\nSave results to %s' % filename)
    fontsize = 20
    if isinstance(results, list):
        plt.figure()
        plt.plot(range(len(results)), results, label='loss')
        plt.title('domain: %s' % domain)
        plt.xlabel('episodes', fontsize=fontsize)
        plt.legend(loc='best', fontsize=fontsize)
        plt.xticks(fontsize=fontsize)  
        plt.yticks(fontsize=fontsize) 
        plt.savefig(filename, format='pdf')
        print('Success\n')

    else:
        plt.figure(figsize=(16, 20)) # , dpi=300
        plt.subplot(311)
        x = range(len(results['rec']))
        plt.plot(x, results['rec'], label='rec')
        plt.plot(x, results['pre'], label='pre')
        plt.plot(x, results['f1'], label='f1')
        plt.title('domain: %s' % domain, fontsize=fontsize)
        plt.xlabel('episodes', fontsize=fontsize)
        plt.legend(loc='best', fontsize=fontsize)
        plt.xticks(fontsize=fontsize)  
        plt.yticks(fontsize=fontsize) 

        plt.subplot(312)
        plt.plot(range(len(results['rw'])), results['rw'], label='reward')
        plt.xlabel('episodes', fontsize=fontsize)
        plt.legend(loc='best', fontsize=fontsize)
        plt.xticks(fontsize=fontsize)  
        plt.yticks(fontsize=fontsize) 

        if 'loss' in results:
            plt.subplot(313)
            plt.plot(range(len(results['loss'])), results['loss'], label='loss')
            plt.xlabel('episodes', fontsize=fontsize)
            plt.legend(loc='best', fontsize=fontsize)
            plt.xticks(fontsize=fontsize)  
            plt.yticks(fontsize=fontsize) 
        
        plt.subplots_adjust(wspace=0.5,hspace=0.5)
        plt.savefig(filename, format='pdf')
        print('Success\n')


def ten_fold_split_ind(num_data, fname, k, random=True):
    """
    Split data for 10-fold-cross-validation
    Split randomly or sequentially
    Retutn the indecies of splited data
    """
    print('Getting tenfold indices ...')
    if os.path.exists(fname):
        print('Loading tenfold indices from %s\n' % fname)
        return load_pkl(fname)
    n = num_data/k
    indices = []

    if random:
        tmp_inds = np.arange(num_data)
        np.random.shuffle(tmp_inds)
        for i in range(k):
            if i == k - 1:
                indices.append(tmp_inds[i*n: ])
            else:
                indices.append(tmp_inds[i*n: (i+1)*n])
    else:
        for i in range(k):
            indices.append(range(i*n, (i+1)*n))

    save_pkl(indices, fname)
    return indices


def index2data(indices, data):
    print('Spliting data according to indices ...')
    folds = {'train': [], 'valid': []}
    if type(data) == dict:
        keys = data.keys()
        print('data.keys: {}'.format(keys))
        num_data = len(data[keys[0]])
        for i in range(len(indices)):
            valid_data = {}
            train_data = {}
            for k in keys:
                valid_data[k] = []
                train_data[k] = []
            for ind in range(num_data):
                for k in keys:
                    if ind in indices[i]:
                        valid_data[k].append(data[k][ind])
                    else:
                        train_data[k].append(data[k][ind])
            folds['train'].append(train_data)
            folds['valid'].append(valid_data)
    else:
        num_data = len(data)
        for i in range(len(indices)):
            valid_data = []
            train_data = []
            for ind in range(num_data):
                if ind in indices[i]:
                    valid_data.append(data[ind])
                else:
                    train_data.append(data[ind])
            folds['train'].append(train_data)
            folds['valid'].append(valid_data)

    return folds


def timeit(f):
    def timed(*args, **kwargs):
        start_time = time.time()
        result = f(*args, **kwargs)
        end_time = time.time()

        print("   [-] %s : %2.5f sec" % (f.__name__, end_time - start_time))
        return result
    return timed

def get_time():
    return time.strftime("%Y-%m-%d_%H:%M:%S", time.gmtime())


def save_pkl(obj, path):
    with open(path, 'wb') as f:
        pickle.dump(obj, f)


def load_pkl(path):
    with open(path, 'rb') as f:
        obj = pickle.load(f)
        return obj

if __name__ == '__main__':
    import sys
    pos_tagging(sys.argv[1], sys.argv[2])