# coding: utf-8
import re
import os
import ipdb
import json
import pickle
import argparse
import numpy as np
from tqdm import tqdm
from utils import timeit, print_args, QuitProgram


def build_state_sequence_training_data(domain):
    #ipdb.set_trace()
    data = pickle.load(open('%s/refined_%s_data.pkl' % (domain, domain), 'rb'))[-1]
    train_data = []
    state_types = {}
    for text in data:
        for sent in text:
            context = [sent['last_sent'], sent['this_sent'], sent['next_sent']]
            for act in sent['acts']:
                act_name = (sent['last_sent'] + sent['this_sent'])[act['act_idx']]
                next_state = act['state']
                state_type = act['state_type']
                a_sample = {'context': context, 'act_name': act_name, 
                            'next_state': next_state, 'state_type': state_type}
                train_data.append(a_sample)
                
                if state_type in state_types:
                    state_types[state_type] += 1
                else:
                    state_types[state_type] = 1
    print(len(train_data))
    print(state_types)
    #pickle.dump([state_types, train_data], open('%s/state_sequence_data.pkl'%domain, 'wb'))
    json.dump([state_types, train_data], open('%s/state_sequence_data.json'%domain, 'w'), indent=4)


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
    num = constant + numerator / denominator if denominator > 0 else 0
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


    def build_dict(self, key_name):
        from nltk.parse.stanford import StanfordDependencyParser
        core = '/Users/fengwf/stanford/stanford-corenlp-3.7.0.jar'
        model = '/Users/fengwf/stanford/english-models.jar'
        self.parser = StanfordDependencyParser(path_to_jar=core, path_to_models_jar=model,
                                                encoding='utf8', java_options='-mx2000m')
        print('Loading data ...')
        data = pickle.load(open('RecipeDatasets/all_mm_recipes.pkl'))
        objs = {}
        adjs = {}
        vbds = {}
        all_sents = [] 
        print('Processing %s ...' % key_name)
        #ipdb.set_trace()
        for i in tqdm(xrange(len(data))):
            text = data[i]
            sents = [transform_digits(i.lower()) for i in text[key_name]]
            try:
                if key_name == 'Steps':
                    self.parse_steps(sents, all_sents)
                else:
                    self.parse_ingredients(sents, all_sents)
            except AssertionError:
                continue
            except KeyboardInterrupt:
                break
            except:
                continue
        
        if key_name == 'Steps':
            with open('RecipeDatasets/steps_dependency.pkl', 'w') as f:
                print('\n Saving file ...')
                pickle.dump(all_sents, f)
                print(' Success!\n')
        else:
            with open('RecipeDatasets/obj_dict.pkl', 'w') as f:
                print('\n Saving file ...')
                pickle.dump({'objs': objs, 'adjs': adjs, 'vbds': vbds, 'all_sents': all_sents}, f)
                print(' Success!\n')


    def parse_ingredients(self, sents, all_sents):
        dep = self.parser.raw_parse_sents(sents)
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
                    continue
            all_sents.append(concurrent_sent)


    def parse_steps(self, sents, all_sents):
        # save all dependency results of text['Steps'] to file
        dep = self.parser.raw_parse_sents(sents)
        dep_list = []
        #words_list = []
        for ind in xrange(len(sents)):
            lines = [l.split() for l in str(dep.next().next().to_conll(10)).split('\n')]
            lines = filter_empty(lines)
            #words = [' '] * (int(lines[-1][0]) + 1)
            dependency = []
            for line in lines:
                try:
                    dependency.append([line[0], line[1], line[3], line[6], line[7]])
                    #words[int(line[0])] = line[1]
                except KeyboardInterrupt:
                    raise KeyboardInterrupt
                except: # end of the line or not enough components
                    continue
            dep_list.append(dependency)
            #words_list.append(words)
        #all_sents.append({'words': words_list, 'dep': dep_list})
        all_sents.append(dep_list)


    def convert_texts(self, filename, output=[], outfile='', save_file=False):
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

    
    def convert_texts_main(self, convert_mode):
        output = []
        home = 'RecipeDatasets/mmf_files/'
        outfile = 'RecipeDatasets/%s_recipes' % convert_mode
        if convert_mode == 'all':
            files = [f for f in os.listdir(home) if f.endswith('.mmf')]
            max_file_ind = len(files) - 1
            for i, name in enumerate(files):
                save_file = False if i < max_file_ind else True
                output = self.convert_texts(home + name, output, outfile, save_file)
        else:
            for c in 'abcdefghijk':
                output = self.convert_texts('Mm13000%s.mmf' % c, output, outfile)
            output = self.convert_texts('mm2155re.mmf', output, outfile)
            output = self.convert_texts('misc2600.mmf', output, outfile, save_file=True)


    def load_driver(self):
        from selenium import webdriver
        self.driver = webdriver.Chrome('~/Desktop/chromedriver')


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



class TextLabeler(object):
    """docstring for TextLabeler"""
    def __init__(self, args):
        self.domain = args.domain
        self.num_texts = args.num_texts
        self.int2type = {1: 'essential', 2: 'optional', 3: 'exclusive'}
        filename = '%s_black_list.txt' % args.domain
        if os.path.exists(filename):
            self.black_list = map(int, open(filename).read().split())
        else:
            self.black_list = []
        if args.domain == 'recipe':
            self.input_file = 'RecipeDatasets/all_mm_recipes.pkl'
            self.save_labeled_data = 'RecipeDatasets/recipes_labeled_data.pkl'
        else:
            dom2name = {'car': 'cars-%26-other-vehicles',
                    'home': 'home-and-garden',
                    'food': 'food-and-entertaining',
                    'computer': 'computers-and-electronics',
                    }
            self.input_file = 'wikihow/%s_500_words' % dom2name[args.domain]
            self.save_labeled_data = 'wikihow/labeled_%s_data.pkl' % dom2name[args.domain]
        

    def add_state(self):
        self.domain = 'wikihow'
        self.save_labeled_data = '%s/refined_%s_data.pkl' % (self.domain, self.domain)
        with open(self.save_labeled_data, 'rb') as f:
            print('Load data from %s...\n' % self.save_labeled_data)
            last_text, last_sent, data = pickle.load(f)
            print('last_text: %d\t last_sent: %d\n' % (last_text, last_sent))
        while True:
            init = raw_input('Input last text num and sent num\n')
            if not init:
                print('No input, program exit!\n')
            if len(init.split()) == 2:
                start_text = int(init.split()[0])
                start_sent = int(init.split()[1])
                break
        ipdb.set_trace()
        break_flag = False
        num_texts = len(data)
        for i in range(start_text, num_texts):
            num_sents = len(data[i])
            start = start_sent if i == start_text else 0
            for j in range(start, num_sents):
                try:
                    if j < num_sents - 1:
                        next_sent = data[i][j + 1]['this_sent']
                    else:
                        next_sent = []
                    data[i][j]['next_sent'] = next_sent
                    print('\nT%d of %d, S%d of %d:' % (i, num_texts, j, num_sents))
                    words = data[i][j]['last_sent'] + data[i][j]['this_sent'] + data[i][j]['next_sent']
                    ind = self.print_sent(data[i][j]['last_sent'], 0, 'LAST')
                    ind = self.print_sent(data[i][j]['this_sent'], ind, 'THIS')
                    ind = self.print_sent(data[i][j]['next_sent'], ind, 'NEXT')

                    for k in range(len(data[i][j]['acts'])):
                        act_idx = data[i][j]['acts'][k]['act_idx']
                        obj_idxs = data[i][j]['acts'][k]['obj_idxs']
                        act_type = data[i][j]['acts'][k]['act_type']
                        # map the indices of the objects to the corresponding words
                        obj_names = [[], []]
                        for l in range(2):
                            for m in obj_idxs[l]:
                                if m >= 0:
                                    obj_names[l].append(words[m])
                                else:
                                    obj_names[l].append('NULL')
                        print('\t act_type: %s' % self.int2type[act_type])
                        print('\t %s(%s)' % (words[act_idx], ','.join(obj_names[0])))
                        if obj_idxs[1]:
                            print('\t %s(%s)' % (words[act_idx], ','.join(obj_names[1])))    

                        # add state transition
                        state, state_type = self.next_state(words[act_idx], obj_idxs, obj_names)
                        data[i][j]['acts'][k]['state'] = state
                        data[i][j]['acts'][k]['state_type'] = state_type
                except:
                    break_flag = True
                    break
            # save file after tagged each text
            with open(self.save_labeled_data, 'wb') as f:
                pickle.dump([i, j, data], f)

            if break_flag:
                break
        
        with open(self.save_labeled_data, 'wb') as f:
            pickle.dump([i, j, data], f)
            print('last_text: %d\t last_sent: %d\n' % (i, j))


    def text_labeling(self):
        # main function for annotating the texts
        print('\nLoad data from %s...\n' % self.input_file)
        texts = pickle.load(open(self.input_file))
        for ind in self.black_list:
            texts.pop(ind)

        if os.path.exists(self.save_labeled_data):
            with open(self.save_labeled_data, 'rb') as f:
                print('Load data from %s...\n' % self.save_labeled_data)
                last_text, last_sent, data = pickle.load(f)
                print('last_text: %d\t last_sent: %d\n' % (last_text, last_sent))
            while True:
                init = raw_input('Input last text num and sent num\n')
                if not init:
                    print('No input, program exit!\n')
                if len(init.split()) == 2:
                    start_text = int(init.split()[0])
                    start_sent = int(init.split()[1])
                    break
            ipdb.set_trace()
        else:
            start_text = start_sent = 0
            data = [[] for _ in range(self.num_texts)]
        
        for i in range(start_text, self.num_texts):
            text = texts[i]['Steps'] if self.domain == 'recipe' else texts[i]
            #text = [re.sub(r'[,;]', '', s.lower()).split() for s in text]
            text = [transform_digits(s) for s in text]
            num_sents = len(text)
            print('\ntext %d: total %d words\n' % (i, sum([len(t) for t in text])))
            if len(data[i]) > 0: #self.domain != 'cooking' and i == start_text and 
                sents = data[i]
            else:
                sents = [{} for _ in range(num_sents)]
            try:
                if i != start_text:
                    start_sent = 0       
                for j in range(start_sent, num_sents):
                    sent = {}
                    this_sent = text[j]
                    # print two sentences, used for coreference resolution
                    last_sent = text[j - 1] if j > 0 else ''
                    next_sent = text[j + 1] if j < num_sents - 1 else ''
                    sent['last_sent'] = re.sub(r'[,;]', '', last_sent.lower()).split()
                    sent['this_sent'] = re.sub(r'[,;]', '', this_sent.lower()).split()
                    sent['next_sent'] = re.sub(r'[,;]', '', next_sent.lower()).split()
                    sent['acts'] = []
                    raw_words = [s.split() for s in [last_sent, this_sent, next_sent]]
                    words = sent['last_sent'] + sent['this_sent'] + sent['next_sent']
                    assert len(words) == sum([len(s) for s in raw_words])
                    print('\nT%d of %d, S%d of %d:' % (i, self.num_texts, j, num_sents))
                    ind = self.print_sent(raw_words[0], 0, 'LAST')
                    ind = self.print_sent(raw_words[1], ind, 'THIS')
                    ind = self.print_sent(raw_words[2], ind, 'NEXT')

                    sent = self.label_a_sent(sent, words, raw_words)
                    if len(sents) < num_sents:
                        sents.append({})
                    sents[j] = sent

                # save file after tagged each text
                with open(self.save_labeled_data, 'wb') as f:
                    pickle.dump([i, j, data], f)
            
            except Exception as e:
                print('Error:', e)
                if len(data) < self.num_texts:
                    data.append([])
                data[i] = sents
                with open(self.save_labeled_data, 'wb') as f:
                    pickle.dump([i, j, data], f)
                    break_flag = True
                    print('last_text: %d\t last_sent: %d\n' % (i, j))
                    break
            if len(data) < self.num_texts:
                    data.append([])
            data[i] = sents
        
        # save file
        with open(self.save_labeled_data, 'wb') as f:
            pickle.dump([i, j, data], f)
            break_flag = True
            print('last_text: %d\t last_sent: %d\n' % (i, j))


    def print_sent(self, sent, ind, flag):
        print('%s: ' % flag),
        for w in sent:
            print('%s(%d)'%(w, ind)),
            ind += 1
        print('')
        return ind


    def label_a_sent(self, sent, words, raw_words):
        num_words = len(words)
        while True:
            inputs = raw_input('\nInput an action and object indices:\n').strip()
            if not inputs:
                break
            #ipdb.set_trace()
            # input contains at least three numbers, 
            # indicating action type, action index and object indices
            nums = inputs.split()
            if len(nums) <= 2:
                if inputs == 'q':
                    raise QuitProgram()
                elif inputs == 'r': # revise a sent
                    print(' '.join(sent['this_sent']))
                    text[j] = input('Input right sentence\n').strip()
                    sent['this_sent'] = re.sub(r'[,;]', '', text[j].lower()).split()
                    words = sent['last_sent'] + sent['this_sent'] + sent['next_sent']
                    ind = self.print_sent(raw_words[0], 0, 'LAST')
                    ind = self.print_sent(text[j], ind, 'THIS')
                    ind = self.print_sent(raw_words[2], ind, 'NEXT')
                    continue
                else:
                    continue

            # cope with the action type
            act_type = int(nums[0])
            if act_type not in [1, 2, 3]: # essential, optional, exclusive
                print('Wrong act_type!')
                continue
            if act_type == 3:
                related_acts = input('Enter its related actions (indices):\n')
                related_acts = [int(r) for r in related_acts.split()]
                if len(related_acts) == 0:
                    print('You should input related_acts!\n')
                    continue
                print('\tRelated actions: {}'.format([words[idx] for idx in related_acts]))
            else:
                related_acts = []

            # cope with the indices of the objects
            act_idx = int(nums[1])
            if act_idx >= num_words:
                print('action index %d out of range' % act_idx)
                continue
            obj_idxs = [[], []]
            continue_flag = False
            # Add essential object indices
            for idx in map(int, nums[2].split(',')):
                if idx >= num_words:
                    print('object index %d out of range' % idx)
                    continue_flag = True
                    break
                obj_idxs[0].append(idx)
            if continue_flag:
                continue
            # Add exclusive object indices if necessary
            if len(nums) >= 4:
                for idx in map(int, nums[3].split(',')):
                    if idx >= num_words:
                        print('object index %d out of range' % idx)
                        continue_flag = True
                        break
                    obj_idxs[1].append(idx)
            if continue_flag:
                continue
            
            # map the indices of the objects to the corresponding words
            obj_names = [[], []]
            for l in range(2):
                for m in obj_idxs[l]:
                    if m >= 0:
                        obj_names[l].append(words[m])
                    else:
                        obj_names[l].append('NULL')
            print('\t act_type: %s' % self.int2type[act_type])
            print('\t %s(%s)' % (words[act_idx], ','.join(obj_names[0])))
            if obj_idxs[1]:
                print('\t %s(%s)' % (words[act_idx], ','.join(obj_names[1])))
            
            state = self.next_state(words[act_idx], obj_idxs, obj_names)
            sent['acts'].append({'act_idx': act_idx, 'obj_idxs': obj_idxs, 
                                'state': state, 'state_type': state_type,
                                'act_type': act_type, 'related_acts': related_acts})
        return sent
        

    def next_state(self, act, obj_idxs, objs):
        #ipdb.set_trace()
        act = act.lower()
        options = '1: vn1+o  2: vn2+o  3: p(o1, o2)  4: o3  5: p(o2, o3)'
        inputs = raw_input('\n\t Input new states: %s\n' % options)
        if not inputs:
            return []
        inputs = inputs.strip().split()
        state_type = int(inputs[0])
        #objs = [[words[i] for i in obj_idxs[j]] for j in range(len(obj_idxs))]
        # <vbn + obj>
        if state_type == 1: 
            try:
                vbn = en.verb.past_participle(act)
            except:
                vbn = raw_input('\n\t Key Error! Input the past participle of "%s":\n' % act).strip()
                if vbn in ['ed', 'n', 'd']:
                    vbn = act + vbn
            state = [[vbn, '_'.join(obj)] for obj in objs if obj]
            for i in range(len(state)):
                print('\t  %s(%s)' % (state[i][0], state[i][1]))
        # <new vbn + obj>
        elif state_type == 2:
            vbn = inputs[1] #raw_input('\n\t Input the attribute of the objects: \n').strip()
            state = [[vbn, '_'.join(obj)] for obj in objs if obj]
            for i in range(len(state)):
                print('\t  %s(%s)' % (state[i][0], state[i][1]))
        # <preposition + obj1 + obj2>
        elif state_type == 3: 
            prep, obj2 = inputs[1: ]
            state = [[prep, obj2, '_'.join(obj)] for obj in objs if obj]
            for i in range(len(state)):
                print('\t  %s(%s, %s)' % (state[i][0], state[i][1], state[i][2]))
        # <new objects>
        elif state_type == 4:
            state = [[inputs[1]]]
            print('\t  new obj: %s' % state)
        # <new objects + preposition> or <vnb + obj + preposition>
        else: #state_type == 5:
            # 既包含动作，又包含介词短语表示状态，如：In a bowl mix flour salt and pepper.
            if len(inputs) == 3:
                prep, obj2 = inputs[1: ]
                try:
                    vbn = en.verb.past_participle(act)
                except:
                    vbn = raw_input('\n\t Key Error! Input the past participle of "%s":\n' % act).strip()
                new_obj = [vbn] + objs[0]
            else:
                prep, obj2, new_obj = inputs[1: ]
            if isinstance(new_obj, list):
                state = [[prep, obj2, '_'.join(new_obj)]]
            else:
                state = [[prep, obj2, new_obj]]
            for i in range(len(state)):
                print('\t  new obj: %s(%s, %s)' % (state[i][0], state[i][1], state[i][2]))
        return state, state_type



    
if __name__ == '__main__':
    # build_state_sequence_training_data('cooking')
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain',         type=str,   default='recipe',       help='')
    parser.add_argument('--model',          type=str,   default='labeling',     help='')
    parser.add_argument('--function',       type=str,   default='build_dict',   help='')
    parser.add_argument('--convert_mode',   type=str,   default='all_mm',       help='')
    parser.add_argument('--key_name',       type=str,   default='Steps',        help='')
    parser.add_argument('--num_texts',      type=int,   default=1000,           help='')
    parser.add_argument('--max_words',      type=int,   default=500,            help='')
    args = parser.parse_args()
    print_args(args)
    
    if args.model == 'scrap':
        processor = MainScraper()
        #ipdb.set_trace()
        if args.function == 'build_dict':
            processor.build_dict(args.key_name)
        else:
            processor.convert_texts_main(args.convert_mode)
    
    # else args.model is used for text_labeling
    else:
        import en
        model = TextLabeler(args)
        #model.text_labeling()
        model.add_state()





