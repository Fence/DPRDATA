import re
import os
import ipdb
import json
import pickle
import numpy as np
from tqdm import tqdm
from utils import timeit


def transform_digits(sent):
    #ipdb.set_trace()
    div_ind = sent.find('/')
    if div_ind < 0:
        return sent
    # find denominator
    max_char = len(sent) - 1
    denominator = '' #re.match(r'\d+', sent[div_ind: ])
    ind = div_ind + 1
    while ind <= max_char and sent[ind].isdigit():
        denominator += sent[ind]
        ind += 1
    if denominator == '':
        return sent
    denominator = float(denominator)
    end = ind
    # find numerator
    numerator = ''
    ind = div_ind - 1
    while ind >= 0 and sent[ind].isdigit():
        numerator = sent[ind] + numerator
        ind -= 1
    numerator = float(numerator) if numerator else 0.0
    #
    constant = ''
    if ind > 0 and sent[ind] == ' ':
        ind -= 1
        # find constant
        while ind >= 0 and sent[ind].isdigit():
            constant = sent[ind] + constant
            ind -= 1
    #
    if constant:
        start = ind + 1
        constant = float(constant)
    else:
        start = ind + 2 if ind >= 0 else 0
        constant = 0.0
    #
    num = constant + numerator / denominator
    sent = sent[: start] + str(num) + sent[end: ]
    return sent


def filter_only_line(sents):
    return filter(lambda x: len(re.sub(r'-+', '', x)) > 0, sents)


def filter_empty(str_list):
    # filter out the empty elements of a list of strings
    return filter(lambda x: len(x) > 0, str_list)


def filter_line(sents):
    # filter out '-'{2, } strings
    if isinstance(sents, str):
        return re.sub(r'-{1,}|[\(\)]', ' ', sents)
    else:
        return [re.sub(r'-{1,}|[\(\)]', ' ', s) for s in sents]


def isIngredient(sent):
    ind = sent.find('.') # sent.rfind('.') find from right to left
    if ind > 0: # 1. step one # not 1.5 oz.
        if sent[ind - 1].isdigit() and not sent[ind + 1].isdigit():
            return False
        # if ind >= 3 and sent[ind - 3: ind].isalpha(): # EOS, e.g. Cook 30 min.
        #     return False
    if '?' in sent or '!' in sent:
        return False
    if sent[0].isdigit() or sent == ' ' or sent.isupper():
        return True
    # it's possible a step if the sentence contains more than 5 words 
    if len(sent.split()) > 5: 
        return False
    return True


def isEndOfSent(sent):
    #if sent.isupper():
    #    return True
    for w in ['Yield: ', 'Source: ']: # 'Note: ', 'NOTE: ', 
        if sent.startswith(w):
            return True
    return False



class MainScraper(object):
    """docstring for MainScraper"""
    def __init__(self):
        self.EOS = ['.', '?', '!']
        self.flags = {'21': ['-----', 'Servings:', 'Pro-Exchange'],
                    '26': ['MMMMM', 'Yield:', 'Recipe'],
                    '13': ['-----', 'Yield:', 'Recipe']}


    def build_dict(self):
        from nltk.parse.stanford import StanfordDependencyParser
        core = '/Users/fengwf/stanford/stanford-corenlp-3.7.0.jar'
        model = '/Users/fengwf/stanford/english-models.jar'
        parser = StanfordDependencyParser(path_to_jar=core, path_to_models_jar=model,
                                            encoding='utf8', java_options='-mx2000m')
        print('Loading data ...')
        data = pickle.load(open('RecipeDatasets/all_mm_recipes.pkl'))
        objs = {}
        adjs = {}
        vbds = {}
        all_sents = [] 
        print('Processing Ingredients ...')
        #ipdb.set_trace()
        for i in tqdm(xrange(len(data))):
            text = data[i]
            sents = [transform_digits(i.lower()) for i in text['Ingredients']]
            try:
                dep = parser.raw_parse_sents(sents)
                for ind in xrange(len(sents)):
                    concurrent_sent = [[], [], []] # NN, JJ, VBD/VBN/VBG
                    lines = [l.split() for l in str(dep.next().next().to_conll(10)).split('\n')]
                    for line in lines:
                        try:
                            ind, word, pos, component = line[0], line[1], line[3], line[7]
                            if len(word) <= 2: # words of units (e.g. x, T, ds etc.)
                                continue
                            if pos in ['NN', 'NNS', 'NNP', 'NNPS']:
                                concurrent_sent[0].append(word)
                                if word in objs:
                                    objs[word] += 1
                                else:
                                    objs[word] = 1
                            elif pos in ['JJ', 'JJR', 'JJS']:
                                concurrent_sent[1].append(word)
                                if word in adjs:
                                    adjs[word] += 1
                                else:
                                    adjs[word] = 1
                            elif pos in ['VBD', 'VBN', 'VBG']:
                                concurrent_sent[2].append(word)
                                if word in vbds:
                                    vbds[word] += 1
                                else:
                                    vbds[word] = 1
                        except KeyboardInterrupt:
                            raise KeyboardInterrupt
                        except: # end of the line or not enough components
                            #ipdb.set_trace()
                            pass
                    all_sents.append(concurrent_sent)
            except AssertionError:
                continue
            except KeyboardInterrupt:
                break
        #ipdb.set_trace()
        with open('RecipeDatasets/obj_dict.pkl', 'w') as f:
            print('\n Saving file ...')
            pickle.dump({'objs': objs, 'adjs': adjs, 'vbds': vbds, 'all_sents': all_sents}, f)
            print(' Success!\n')



    def convert_texts(self, filename, output=[], outfile='', save_file=True):
        # convert *.mmf file to structured data={Title, Categories, Yield, Ingredients, Steps}
        #ipdb.set_trace()
        print('Processing file: %s' % filename)
        data = open(filename).read().strip()
        data = re.sub(r'[\x14\+\*\~\#]+', '', data) # remove the explanation marks
        wrong_text_flag = False
        # comfirm spliter, yield_flag, start_flag
        if data.startswith('---------- Pro-Exchange'):
            spliter, yield_flag, start_flag = self.flags['21']
        elif data.startswith('---------- Recipe'):
            spliter, yield_flag, start_flag = self.flags['13']
        elif data.startswith('MMMMM----- Recipe'):
            spliter, yield_flag, start_flag = self.flags['26']
        else:
            print('\n Wrong file type!\n')
            #ipdb.set_trace()
            lines = filter_empty([t.strip() for t in re.split(r'[\r\n]', data)])
            spliter = '-----'
            start_flag = filter_empty(lines[0].split(spliter))[0].strip()
            yield_flag = lines[3].split()[0]
            wrong_text_flag = True
            #return output
        
        texts = data.split(spliter)
        texts = filter_line(texts)
        texts = [filter_empty([s.strip() for s in re.split(r'[\r\n]', t)]) for t in texts]
        texts = filter_empty(texts)

        #
        text_ind = len(texts) - 1
        while text_ind > 0:
            # read from back to front, start_flag is a flag indicating the start of a recipe
            try:
                text = texts[text_ind]
                while not text[0].startswith(start_flag) and text_ind > 0:
                    text_ind -= 1
                    text = texts[text_ind] + text
                #if wrong_text_flag:
                #    text = filter_only_line(text)
                
                Title = filter_line(text[1].split('Title:')[-1]).strip()
                Categories = [c.strip() for c in text[2].split('Categories:')[1].split(',')]
                Categories = filter_empty(filter_line(Categories))
                Yield = filter_line(text[3].split('%s' % yield_flag)[-1]).strip()

                ind = 4
                Ingredients = []
                max_sent_ind = len(text) - 1
                mater = filter_line(text[ind])
                while isIngredient(mater): #mater[0].isdigit() or isIngredient(mater):
                    #if len(mater) >= 2 and mater[1] == '.': # these are sentences of steps
                    #    break
                    if mater[0].isdigit() and ind < max_sent_ind:
                        next_line = filter_line(text[ind + 1])
                        if not next_line[0].isdigit() and isIngredient(next_line):
                            ind += 1
                            mater = mater + ' ' + filter_line(text[ind])
                    if len(mater) > 1 and mater[-1] != ':':
                        Ingredients.append(mater)
                    if ind < max_sent_ind:
                        ind += 1
                        mater = filter_line(text[ind])
                    else:
                        break

                sent = ''
                Steps = []
                while ind <= max_sent_ind:
                    sent = text[ind] # some sentences are split by \n becuase it's too long
                    while sent[-1] not in self.EOS and ind < max_sent_ind:
                        ind += 1
                        sent = sent + ' ' + text[ind] # join them together

                    if isEndOfSent(sent) and len(Steps) > 0:
                        break
                    sent = filter_line(sent)
                    sents = filter_empty([s.strip() for s in re.split(r'[\?\!\.]', sent)])
                    Steps.extend(sents)
                    ind += 1
                if len(Steps) > 0:
                    output.append({'Title': Title, 'Categories': Categories, 
                        'Yield': Yield, 'Ingredients': Ingredients, 'Steps': Steps})
                    #print('text_ind: %d \t len(output): %d' % (text_ind, len(output)))
                else:
                    ipdb.set_trace()
            except Exception as e:
                #print(e)
                pass

            text_ind -= 1

        #ipdb.set_trace()
        print('text_ind: %d \t len(output): %d' % (text_ind, len(output)))
        if save_file: # save data from different *.mmf files to a single file
            if outfile:
                filename = outfile
            print('Saving file ...')
            with open('%s.pkl' % filename, 'w') as f:
                pickle.dump(output, f)
            with open('%s.txt' % filename, 'w') as f:
                for t in output:
                    f.write('Title: {}\nCategories: {}\nYield: {}\n'.format(
                        t['Title'], ', '.join(t['Categories']), t['Yield']))
                    f.write('Ingredients: \n\t{}\nSteps: \n\t{}\n\n'.format(
                        '\n\t'.join(t['Ingredients']), '\n\t'.join(t['Steps'])))
            print('Success!\n')

        return output

    

    def load_driver(self):
        from selenium import webdriver
        self.driver = webdriver.Chrome('~/Desktop/chromedriver')


    def get_recipes_pages(self):
        pass


    def get_text_from_page(self, url):
        self.driver.get(url)
        elements = self.driver.find_elements_by_xpath('//tr/td')
        if len(elements) >= 2:
            text = [t.strip() for t in e[1].text.split('\n')]
            text = filter_empty(text)
            assert text[1].startswith('MMMMM')
            Title = text[0]
            Categories = filter_empty(text[3].split('Categories:')[1].split(','))
            Yield = text[4].split('Yield: ')[-1]

        ind = 5
        Ingredients = []
        while isdigit(text[ind][0]):
            Ingredients.append(text[ind])
            ind += 1

        sent = ''
        num_sents = len(text)
        Steps = []
        while ind < num_sents - 1:
            sent = text[ind]
            while sent[-1] not in self.EOS and ind < num_sents:
                ind += 1
                sent += text[ind]
            sents = filter_empty(re.split(r'[\?\!\.]', sent))
            Steps.extend(sents)
        assert text[-1].endswith('MMMMM')
        
        return {'Title': Title, 'Categories': Categories, 'Yield': Yield, 
                'Ingredients': Ingredients, 'Steps': Steps}

    
if __name__ == '__main__':
    processor = MainScraper()
    #ipdb.set_trace()
    processor.build_dict()

    # outfile = 'RecipeDatasets/all_recipes'
    # output = []
    # # output = processor.convert_texts('mm2155re', output, outfile)
    # # output = processor.convert_texts('misc2600', output, outfile)
    # # for c in 'abcdefghijk':
    # #     output = processor.convert_texts('Mm13000%s'%c, output, outfile)
    # home = 'RecipeDatasets/mmf_files/'
    # files = [f for f in os.listdir(home) if f.endswith('.mmf')]
    # max_file_ind = len(files) - 1
    # for i, name in enumerate(files):
    #     save_file = False if i < max_file_ind else True
    #     output = processor.convert_texts(home + name, output, outfile, save_file)






