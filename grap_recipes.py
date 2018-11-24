import re
import ipdb
import json
import pickle
import numpy as np
from selenium import webdriver
from utils import timeit


def filter_empty(str_list):
    # filter out the empty elements of a list of strings
    return filter(lambda x: len(x) > 0, str_list)


def isIngredient(sent):
    for mark in [',', '.', '?', '!','(', ')']: # ';'
        if mark in sent:
            return False
    return True


def isEndOfSent(sent):
    return sent.isupper() or sent.startswith('Yield: ') or sent.startswith('Source: ')



class MainScraper(object):
    """docstring for MainScraper"""
    def __init__(self):
        self.EOS = ['.', '?', '!']
        self.explanation_marks = [':', '-']


    def convert_texts(self, filename, spliter, yield_flag, start_flag):
        data = open('RecipeDatasets/%s.mmf' % filename).read()
        data = re.sub(r'[\x14\+\*]+', '', data)
        texts = data.split(spliter)
        texts = [filter_empty([s.strip() for s in re.split(r'[\r\n]', t)]) for t in texts]
        texts = filter_empty(texts)

        ipdb.set_trace()
        output = []
        text_ind = len(texts) - 1
        while text_ind > 0:
            # read from back to front
            try:
                text = texts[text_ind]
                while not text[0].startswith(start_flag) and text_ind > 0:
                    text_ind -= 1
                    text = texts[text_ind] + text
                
                Title = text[1].split('Title:')[-1].strip()
                Categories = [c.strip() for c in text[2].split('Categories:')[1].split(',')]
                Categories = filter_empty(Categories)
                Yield = text[3].split('%s:' % yield_flag)[-1].strip()

                ind = 4
                Ingredients = []
                while text[ind][0].isdigit() or isIngredient(text[ind]):
                    if text[ind][-1] not in self.explanation_marks:
                        Ingredients.append(text[ind])
                    ind += 1

                sent = ''
                num_sents = len(text) - 1
                Steps = []
                while ind < num_sents:
                    sent = text[ind]
                    while sent[-1] not in self.EOS and ind < num_sents:
                        ind += 1
                        sent = sent + ' ' + text[ind]

                    if isEndOfSent(sent):
                        break
                    sents = filter_empty([s.strip() for s in re.split(r'[\?\!\.]', sent)])
                    Steps.extend(sents)
                    ind += 1

                output.append({'Title': Title, 'Categories': Categories, 
                    'Yield': Yield, 'Ingredients': Ingredients, 'Steps': Steps})
                print('text_ind: %d \t len(output): %d' % (text_ind, len(output)))
            except Exception as e:
                print(e)

            text_ind -= 1

        ipdb.set_trace()
        print('Saving file ...')
        with open('RecipeDatasets/%s.pkl' % filename, 'w') as f:
            pickle.dump(output, f)
        with open('RecipeDatasets/%s.txt' % filename, 'w') as f:
            for t in output:
                f.write('Title: {}\nCategories: {}\nYield: {}\n'.format(
                    t['Title'], ', '.join(t['Categories']), t['Yield']))
                f.write('Ingredients: \n\t{}\nSteps: \n\t{}\n\n'.format(
                    '\n\t'.join(t['Ingredients']), '\n\t'.join(t['Steps'])))
        print('Success!')

    

    def load_driver(self):
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
    processor.convert_texts('mm2155', '-----', 'Servings', 'Pro-Exchange')
    processor.convert_texts('misc2600', 'MMMMM', 'Yield', '----- Recipe')





