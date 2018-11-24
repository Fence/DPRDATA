import re
import ipdb
import json
import pickle
import numpy as np
from utils import timeit


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
    if sent == ' ' or sent.isupper():
        return True
    for mark in [',', '.', '?', '!']:
        if mark in sent:
            return False
    # it's possible a step if the sentence contains more than 5 words 
    if sent.split() > 5: 
        return False
    return True


def isEndOfSent(sent):
    if sent.isupper():
        return True
    for w in ['Yield: ', 'Note: ', 'Source: ']:
        if sent.startswith(w):
            return True
    return False



class MainScraper(object):
    """docstring for MainScraper"""
    def __init__(self):
        self.EOS = ['.', '?', '!']


    def convert_texts(self, filename, spliter, yield_flag, start_flag, output=[], save_file=''):
        # convert *.mmf file to structured data={Title, Categories, Yield, Ingredients, Steps}
        data = open('RecipeDatasets/%s.mmf' % filename).read()
        data = re.sub(r'[\x14\+\*\~\#]+', '', data) # remove the explanation marks
        texts = data.split(spliter)
        texts = [filter_empty([s.strip() for s in re.split(r'[\r\n]', t)]) for t in texts]
        texts = filter_empty(texts)

        #ipdb.set_trace()
        text_ind = len(texts) - 1
        while text_ind > 0:
            # read from back to front, start_flag is a flag indicating the start of a recipe
            try:
                text = texts[text_ind]
                while not text[0].startswith(start_flag) and text_ind > 0:
                    text_ind -= 1
                    text = texts[text_ind] + text
                
                Title = filter_line(text[1].split('Title:')[-1]).strip()
                Categories = [c.strip() for c in text[2].split('Categories:')[1].split(',')]
                Categories = filter_empty(filter_line(Categories))
                Yield = filter_line(text[3].split('%s:' % yield_flag)[-1]).strip()

                ind = 4
                Ingredients = []
                num_sents = len(text) - 1
                mater = filter_line(text[ind])
                while mater[0].isdigit() or isIngredient(mater):
                    if len(mater) >= 2 and mater[1] == '.': # these are sentences of steps
                        break
                    if mater[0].isdigit() and len(mater.split()) == 2 and ind < num_sents:
                        ind += 1
                        mater = mater + ' ' + filter_line(text[ind])
                    if len(mater) > 1 and mater[-1] != ':':
                        Ingredients.append(mater)
                    if ind < num_sents:
                        ind += 1
                        mater = filter_line(text[ind])
                    else:
                        break

                sent = ''
                Steps = []
                while ind < num_sents:
                    sent = text[ind] # some sentences are split by \n becuase it's too long
                    while sent[-1] not in self.EOS and ind < num_sents:
                        ind += 1
                        sent = sent + ' ' + text[ind] # join them together

                    if isEndOfSent(sent):
                        break
                    sent = filter_line(sent)
                    sents = filter_empty([s.strip() for s in re.split(r'[\?\!\.]', sent)])
                    Steps.extend(sents)
                    ind += 1
                if len(Steps) > 0:
                    output.append({'Title': Title, 'Categories': Categories, 
                        'Yield': Yield, 'Ingredients': Ingredients, 'Steps': Steps})
                    #print('text_ind: %d \t len(output): %d' % (text_ind, len(output)))
            except Exception as e:
                #print(e)
                pass

            text_ind -= 1

        #ipdb.set_trace()
        print('text_ind: %d \t len(output): %d' % (text_ind, len(output)))
        if save_file: # save data from different *.mmf files to a single file
            filename = save_file
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
    file = 'all_recipes'
    output = []
    output = processor.convert_texts('mm2155re', '-----', 'Servings', 'Pro-Exchange', output, file)
    output = processor.convert_texts('misc2600', 'MMMMM', 'Yield', '----- Recipe', output, file)
    for c in 'abcdefghijk':
        output = processor.convert_texts('Mm13000%s'%c, '-----', 'Yield', 'Recipe', output, file)






