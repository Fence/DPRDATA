#coding:utf-8
import os
import time
import ipdb
import pickle
import logging
from tqdm import tqdm
from gensim.models import Word2Vec

def any2unicode(text, encoding='utf8', errors='strict'):
    """Convert a string (bytestring in `encoding` or unicode), to unicode."""
    if isinstance(text, unicode):
        return text
    return unicode(text, encoding, errors=errors)


def train_wordvec(filename):
    mini_count = 5
    vec_dim = 50 #20
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s',level=logging.INFO)
    #for mini_count in [5, 10]:
    #    for vec_dim in [100, 50]:
    #sentences = MySentences(filename)
    sentences = MyPlanSentence(filename)
    # Word2Vec(sentences=None, size=100, alpha=0.025, window=5, min_count=5, max_vocab_size=None, 
    # sample=0.001, workers=3, min_alpha=0.0001, negative=5, cbow_mean=1, 
    # iter=5, null_word=0, sorted_vocab=1, batch_words=10000, compute_loss=False)
    model = Word2Vec(sentences, min_count=mini_count, size=vec_dim, workers=4, batch_words=10000)
    #model_name = 'mymodel-new-%d-%d' % (mini_count, vec_dim)
    model_name = '%s/%s_model_50_5' % (filename, filename)
    model.wv.save_word2vec_format(model_name, binary=True)


class MyPlanSentence():
    def __init__(self, filename):
        from nltk.stem import WordNetLemmatizer
        self.lemma = WordNetLemmatizer()
        self.filename = filename #['win2k'] #'ehow', 'cooking', 

    def __iter__(self):
        fname = '%s/%s_act_seq_refined.pkl' % (self.filename, self.filename)
        data = pickle.load(open(fname, 'rb'))
        count = 0
        for i in range(len(data)):
            for act, objs in data[i]['act_seq']:
                count += 1
                objs = objs.lower().split('_')
                act = self.lemma.lemmatize(act, pos='v')
                sent = [act] + objs + ['EOS'] # add the end of sentence flag
                yield sent


    def preprocessing(self):
        #ipdb.set_trace()
        fname = '%s/%s_act_seq_refined.pkl' % (self.filename, self.filename)
        f = open('%s/%s_sents.txt' % (self.filename, self.filename), 'w')
        data = pickle.load(open(fname, 'rb'))
        count = 0
        for i in xrange(len(data)):
            f.write('\n\nText %d:\n' % i)
            for act, objs in data[i]['act_seq']:
                count += 1
                objs = objs.lower().split('_')
                act = self.lemma.lemmatize(act, pos='v')
                sent = [act] + objs
                try:
                    f.write('{}\n'.format(' '.join(sent)))
                except Exception as e:
                    print(i, e)
        f.close()



class MySentences(object):
    def __init__(self, dirname, save_file=''):
        self.dirname = dirname
        self.save_file = save_file
 
    def __iter__(self):
        for fname in os.listdir(self.dirname):
            if fname.endswith('all_texts.txt'):
                for line in open(os.path.join(self.dirname, fname)):
                    try:
                        sent = any2unicode(line).split()
                        yield sent
                    except Exception as e:
                        pass

    def text2sent(self, fname):
        text = open(fname).read()
        text = re.sub(r'\n|\r|\"|,|:|;', ' ', text)
        sents = re.sub(r'\. |\! |\? ', '\n', text)#.strip().split('\n')
        return sents

    def test_wikihow(self):
        with open(self.save_file, 'w') as f:
            count = 0
            for subdir in os.listdir(self.dirname):
                if subdir != 'zSubCategory':
                    for fname in os.listdir(self.dirname + subdir):
                        sents = self.text2sent(os.path.join(self.dirname + subdir, fname))
                        f.write(sents)
                        count += 1
                        print('count = %d'%count)
                else:
                    sondir = self.dirname + subdir + '/'
                    for grandsondir in os.listdir(sondir):
                        for fname in os.listdir(sondir + grandsondir):
                            sents = self.text2sent(os.path.join(sondir + grandsondir, fname))
                            f.write(sents)
                            count += 1
                            print('count = %d'%count)

    def test_windows(self):
        with open(self.save_file, 'w') as f:
            count = 0
            for subdir in ['win10_out', 'accounts']:
                for fname in os.listdir(self.dirname + subdir):
                    sents = open(os.path.join(self.dirname + subdir, fname)).read()
                    f.write(sents)
                    count += 1
                    print('count = %d'%count)


    def test_cooking(self):
        with open(self.save_file, 'w') as f:
            count = 0
            for subdir in ['old_out', 'new_out']:
                for fname in os.listdir(self.dirname + subdir):
                    if subdir == 'old_out':
                        sents = self.text2sent(os.path.join(self.dirname + subdir, fname))
                    else:
                        sents = open(os.path.join(self.dirname + subdir, fname)).read()
                    f.write(sents)
                    count += 1
                    print('count = %d'%count)

    def test_navigation(self):
        with open(self.save_file, 'w') as f:
            count = 0
            for fname in os.listdir(self.dirname):
                if fname.endswith('txt'):
                    sents = open(os.path.join(self.dirname, fname)).read()
                    f.write(sents)
                    count += 1
                    print('count = %d'%count)

    def test_ehow(self):
        with open(self.save_file, 'w') as f:
            count = 0
            for fname in os.listdir(self.dirname):
                sents = self.text2sent(os.path.join(self.dirname, fname))
                f.write(sents)
                count += 1
                print('count = %d'%count)





if __name__ == '__main__':
    start = time.time()
    save_file = '/home/fengwf/Documents/DRL_data/all_texts.txt'
    dirname = '/home/fengwf/Documents/DRL_data/'
    
    sent = MyPlanSentence('wikihow')
    sent.preprocessing()
    #ipdb.set_trace()
    train_wordvec('wikihow')
    end = time.time()
    print('\nTotal time cost: %ds\n' % (end-start))
    '''
    import ipdb
    ipdb.set_trace()
    spliter = MySentences(dirname)
    count = 0
    for s in spliter:
        print s
        count += 1
        if count >= 100:
            break
    '''