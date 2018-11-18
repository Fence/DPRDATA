#coding:utf-8
import os
import ipdb
import time
import pickle
import requests
from lxml import etree


def get_articles(name, folder):
    unequal_flag = False
    page = requests.get(home + name).content
    tree = etree.HTML(page)
    #ipdb.set_trace()
    article_name = name.replace('-', ' ')
    intro = tree.xpath('//div[@id="intro"]/p')
    #tasks = tree.xpath('//h3/span[contains(@class, "mw-headline")]')
    tasks = tree.xpath('//div[contains(@class, "section steps")]')
    parts = tree.xpath('//ol[@class="steps_list_2"]')
    if len(intro) == 0:
        print('\t  No intro!\n')
    if len(tasks) == 0:
        print('\t%s  No tasks!\n' % (home + name))
        return {}
    if len(parts) != len(tasks):
        #ipdb.set_trace()
        print('\t%s' % (home + name))
        print('\tlen(parts): %d != len(tasks): %d\n' % (len(parts), len(tasks)))
        if len(parts) == 0:
            return {}
        else:
            if len(parts) > len(tasks):
                unequal_flag = True
            else:
                tasks = tasks[: len(parts)]
            print('\tlen(parts): %d    len(tasks): %d\n' % (len(parts), len(tasks)))
    if len(intro) > 0:
        intro_str = intro[-1].xpath('string(.)'.strip())
    else:
        intro_str = ''

    data = {}
    data['url'] = home + name
    data['title'] = 'How to ' + article_name
    data['intro'] = intro_str
    data['task'] = []
    data['sub_task'] = []
    data['detail'] = []
    if not os.path.exists('new_details/%s' % folder):
        os.system('mkdir new_details/%s' % folder)
    file_name = 'new_details/%s/%s.txt' % (folder, name)
    with open(file_name, 'w') as f:
        f.write('<URL> %s\n\n' % (home + name))
        f.write('<Title> How to %s\n\n' % article_name)
        f.write('<Intro> {}\n\n'.format(intro_str))
        for t in tasks:
            pattern = 'span[contains(@class, "mw-headline")]'
            # two cases, one is h3/span and the other is div_steps/h4/span
            t_name = t.xpath('./*/%s|./*/*/%s' % (pattern, pattern))
            for tn in t_name:
                f.write('<Task> {}\n'.format(tn.xpath('string(.)').strip()))
                data['task'].append(tn.xpath('string(.)').strip())
        f.write('\n')
        if unequal_flag:
            print('\tlen(parts): %d\tlen(tasks): %d\n' % (len(parts), len(data['task'])))

        for p in parts:
            sub_tasks = p.xpath('./*/*/b[@class="whb"]')
            if len(sub_tasks) == 0:
                print('No sub_tasks!\n')
                return {}
            tmp_sub_tasks = []
            for s in sub_tasks:
                f.write('<SubTask> {}\n'.format(s.xpath('string(.)').strip()))
                tmp_sub_tasks.append(s.xpath('string(.)').strip())
            f.write('\n')
            data['sub_task'].append(tmp_sub_tasks)

        for p in parts:
            f.write('\n<Detail>\n')
            details = p.xpath('./*/div[@class="step"]')
            tmp_detail = []
            for d in details:
                f.write(d.xpath('string(.)').strip() + '\n')
                tmp_detail.append(d.xpath('string(.)').strip())
            f.write('\n')
            data['detail'].append(tmp_detail)

    return data


def get_urls(name, url, save_dict):
    print('name: %s\turl: %s%s' % (name, home, url))
    page = requests.get(home + url).content
    tree = etree.HTML(page)

    # article urls
    ahrefs = tree.xpath('//div[contains(@class,"thumbnail")]/a[@href]')
    if name not in save_dict:
        save_dict[name] = {}
        save_dict[name]['page_url'] = []
        save_dict[name]['cate_url'] = [url]
        save_dict['cate_count'] += 1
    for a in ahrefs:
        tmp_url = a.get('href').split('/')[-1]
        if tmp_url not in save_dict[name]['page_url']:
            save_dict[name]['page_url'].append(tmp_url)
            save_dict['page_count'] += 1
    print(save_dict.keys())

    # sub category urls
    bhrefs = tree.xpath('//li[contains(@class,"cat_icon")]/a[@href]')
    chrefs = tree.xpath('//ul[contains(@class, "category_column")]/li/a[@href]')
    sub_cate_urls = []
    if len(bhrefs) > 0:
        for b in bhrefs:
            cate_url = b.get('href').split('/')[-1]
            if cate_url not in save_dict[name]['cate_url']:
                sub_cate_urls.append(cate_url)
                save_dict[name]['cate_url'].append(cate_url)
                save_dict['cate_count'] += 1
    if len(chrefs) > 0:
        for c in chrefs:
            cate_url = c.get('href').split('/')[-1]
            if cate_url not in save_dict[name]['cate_url']:
                sub_cate_urls.append(cate_url)
                save_dict[name]['cate_url'].append(cate_url)
                save_dict['cate_count'] += 1
    print('Total urls: %d\tcates: %d\n' % (save_dict['page_count'], save_dict['cate_count']))

    if name == 'Main-Page':
        for b in sub_cate_urls:
            get_urls(b, b, save_dict)
    else:
        for b in sub_cate_urls:
            get_urls(name, b, save_dict)

#dict_keys(['count', 'Main-Page', 'Category:Food-and-Entertaining', 
#   'Category:Hobbies-and-Crafts', 'Category:Education-and-Communications', 
#   'Category:Computers-and-Electronics', 'Category:Arts-and-Entertainment', 
#   'Category:Health', 'Category:Family-Life', 'Category:Cars-%26-Other-Vehicles', 
#   'Category:Finance-and-Business']
if __name__ == '__main__':
    #import sys
    #reload(sys)
    #sys.setdefaultencoding('gb18030')
    start = time.time()
    fname = 'wikihow_data.pkl'
    save_file = 'cate_urls_dict.pkl'
    new_save_file = 'new_cate_urls_dict.pkl'
    home = "https://www.wikihow.com/"
    
    with open(new_save_file, 'rb') as f0:
        cate_urls_dict = pickle.load(f0)
    last_keys = []
    last_idx = 0
    count = 0
    data = {}
    if os.path.exists(fname):
        with open(fname, 'rb') as f2:
            last_keys, last_idx, count, data = pickle.load(f2)
    #ipdb.set_trace()
    print(cate_urls_dict.keys())
    try:
        for key in cate_urls_dict:
            if key.endswith('count'):
                continue
            #for idx, url in enumerate(cate_urls_dict[key]):
            if key in last_keys:
                print(key, last_idx)
                if key != last_keys[-1]:
                    continue
                start_idx = last_idx
                if data[key][last_idx]:
                    print(data[key][last_idx]['title'])
            else:
                last_keys.append(key)
                start_idx = 0
                data[key] = [{} for i in range(len(cate_urls_dict[key]['page_url']))]
            for idx in range(start_idx, len(cate_urls_dict[key]['page_url'])):
                url = cate_urls_dict[key]['page_url'][idx]
                sub_data = {}
                try:
                    sub_data = get_articles(url, key)
                except Exception as e:
                    print('An Error occurs:',e)
                if len(sub_data) > 0:
                    data[key][idx] = sub_data
                    count += 1
                    print('count: %d  url: %s' % (count, home + url))
                    if count % 1000 == 0:
                        with open(fname, 'wb') as f1:
                            print('Try to save file.')
                            pickle.dump([last_keys, idx, count, data], f1)
                            print('Successfully save %s' % fname)

    except KeyboardInterrupt as e:
        print('\nManually Keyboard Interrupt, try to save file...\n')
    
    with open(fname, 'wb') as f1:
        pickle.dump([last_keys, idx, count, data], f1)
        print('Successfully save %s' % fname)
    '''
    #try:
    cate_urls_dict = {'page_count': 0, 'cate_count': 0}
    #ipdb.set_trace()
    get_urls('Main-Page', 'Main-Page', cate_urls_dict)
    #except Exception as e:
    #    print('An Error occurs:',e)
    with open(save_file, 'wb') as f:
        print('Trying to save file ...')
        pickle.dump(cate_urls_dict, f)
        print('Successfully save %s' % save_file)
    '''
    end = time.time()
    print('Time cost: %.2fs' % (end - start))
