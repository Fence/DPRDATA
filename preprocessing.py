#coding:utf-8
import re
import os
import time
import mysql.connector

output = './win10_out/'#'./long_texts/'
source = './accounts/'#'./wiki_long_texts/'

#wrong_text = [7, 25, 30, 46, 60, 72]
def rewriting():
    """
    数据预处理， 把冗余和错误文本过滤掉
    """
    ind = 0
    dir_list = os.listdir(source)
    for i in range(len(dir_list)):
        if dir_list[i].find('.txt') != -1:
            #print 'Writing text %d, name: "%s"'%(i+1, dir_list[i])
            text = open(source+dir_list[i]).read()
            a = text.find('getElementById')
            if a != -1:
                print a
                print "\n-----text.find('getElementById')-----\n"
                continue
            ind += 1
            f = open(source+str(ind)+'_raw.out','w+')
            f.write(text)
            f.close()

    print '\n\nRewriting done!\n\n'

    for i in range(ind):
        f = open( output + str(i+73) + '.txt', 'w+')
        count = 0
        for line in open( source + str(i+1) + '_raw.out' ):
            #print source + str(i+1) + '.txt'
            if not line.split():
                pass
                #print 'len(line)',len(line),' line: ',line
            else:
                temp_text = ''
                temp_count = 0
                a = re.sub(r'[\.\?\!] ', '\n', line)
                #print '\n\na: ',a
                #print len(a)
                aa = a.split('\n')
                for b in aa:
                    if len(b.split()) == 1:
                        #print '\nlen(b.split()) == 1, pass\n'
                        continue
                    if b.split():
                        #print len(b),'b: ',b
                        c = re.findall(r'[\w-]+', b)
                        temp_count += len(c)
                        d = ' '.join(c)
                        #print '----------c: ',c
                        temp_text = temp_text + d + '\n'
                        #print 'dddd:  %s'%d
                        #print 'temp_count = ',temp_count
                count += temp_count
                if count > 500:
                    f.write('-----LONG_TEXT_SEPARATOR-----\n')
                    count = 0
                f.write(temp_text)

        f.close()


def counter(text_dir):
    """
    计算预处理后的长/短文本的单词总数和文本数
    """
    long_words = 0
    short_words = 0
    count = 0
    lt = 0
    start = 34
    stop = 89
    for i in range(start, stop):
        text = open(text_dir+str(i)+'.txt').read()
        ws = len(text.split())
        a = re.findall(r'-----LONG_TEXT_SEPARATOR-----',text)
        b = len(a)
        if b > 0:
            long_words += ws
            count += b+1
            lt += 1 
            print 'count = %d,  b+1 = %d,  lt = %d'%(count, b+1, lt)
        else:
            short_words += ws
        print 'i = %d,  ws = %d'%(i, ws)
    print 'long_words = %d,  short_words = %d'%(long_words, short_words)
    print 'long_avg = %f,  short_avg = %f'%\
    (long_words/float(lt), short_words/float(stop-start-lt))
     

def count_long_text():
    db = mysql.connector.connect(user='fengwf', password='123', database='test')
    cur = db.cursor()
    result = []
    count = []
    table_name = 'tag_actions5'
    max_text_num = 35
    for i in range(max_text_num):
        get_data = "select * from " + table_name + " where text_num = " + \
        str(i) + " order by sent_num"
        #print 'get_data = %s'%get_data
        print 'text num : %d'%i
        cur.execute(get_data)
        temp = cur.fetchall()
        result.append(temp)
        num = 1
        words = 0
        for j in range(len(temp)):
            sent = temp[j][2].split()
            ws = len(sent)
            if ws == 1 and sent[0] == '-----LONG_TEXT_SEPARATOR-----':
                num += 1
                #print temp[j][2].split()[0]
            else:
                words += ws
        print 'num = %d'%num
        print 'total words: %d\n'%words
        if words > 500:
            print '----- words > 500 -----'
        count.append(num)
    print count
    print 'count = %d'%sum(count)


def reconstruct_SAIL_texts():
    '''
    f = open('out_paragraph.txt','w+')
    for line in open('paragraph.instructions').readlines():
        if re.search(r'Cleaned.+|{}',line) or len(line) <= 1:
            pass
        else:
            #print line
            sents = re.sub(r',','',line)
            sents = re.sub(r'  |\n',' ',sents)
            sents = re.split(r'\. ',sents)
            #print sents
            for s in sents:
                if s:
                    f.write(s+'\n')
    f.close()
    '''
    index = 1
    words = 0
    sents = 0
    f = open(str(index)+'.txt','w+')
    for line in open('out_paragraph.txt').readlines():
        words += len(line.split())
        if words >= 500:
            print '-----Total words in text %d is %d-----' %(index,words-len(line.split()))
            f.close()
            index += 1
            words = len(line.split())
            sents = 0
            f =open(str(index)+'.txt','w+')
        f.write(line)
        sents += 1
        print 'Writing in text %d sentences %d' %(index,sents)


def reconstruct_win2k_texts():
    f = open('split_windows2k_dataset.txt','w+')
    for line in open('windows2k_dataset.txt').readlines():
        if re.search(r'!|@',line) or len(line) <= 1:
            pass
        else:
            #f.write(str(count)+' length: '+str(len(line))+'  '+re.sub(r'<b>|</b>','',line))
            f.write(re.sub(r'<b>|</b>|#|/|\\|,|\(|\)','',line))
    f.close()
    '''
    count = 0
    f = open('out_articles.txt','w+')
    for line in open('articles.txt').readlines():
        count += 1 
        if re.search(r'# |##|#/|@',line) or len(line) <= 1:
            pass
        else:
            #f.write(str(count)+' length: '+str(len(line))+'  '+re.sub(r'<b>|</b>','',line))
            f.write(re.sub(r'<b>|</b>|#','',line))
    print 'Done!'


    sents = []
    f = open('split_articles.txt','w+')
    for line in open('out_articles.txt').readlines():
        temp_sent = re.split(r', |\n| ',line)
        sents.append(temp_sent)
        f.write(' '.join(temp_sent) + '\n') 
    f.close()
    '''
    index = 19
    words = 0
    sents = 0
    f = open(str(index)+'.txt','w+')
    for line in open('split_windows2k_dataset.txt').readlines():
        words += len(line.split())
        if words >= 500:
            print '-----Total words in text %d is %d-----' %(index,words-len(line.split()))
            f.close()
            index += 1
            words = len(line.split())
            sents = 0
            f =open(str(index)+'.txt','w+')
        f.write(line)
        sents += 1
        print 'Writing in text %d sentences %d' %(index,sents)


if __name__ == '__main__':
    #counter('./win10_out/')
    rewriting()