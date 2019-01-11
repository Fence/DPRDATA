## DPR_data

## 文件说明

1. data_labeling.py：旧的动作序列标注的代码，里面包含文本处理以及利用Stanford NLP寻找VPs的代码。需要使用python3运行
2. extract_from_navigation.py：将windows 2000的原始文档（articles），SAIL的原始文档（paragraph instruction），划分为一个个文本
3. grap_recipes.py：新的动作序列标注代码，包含状态序列的标注，需要用到语言工具en，用python2运行
4. grap_wikihow.py：爬虫代码，从wikihow的网页中抓取文本
5. tag_actions_wxpython.py：旧的动作序列标注的代码，利用wxpython写的图形化界面
6. test_gensim.py：利用gensim训练word vectors
7. utilis.py：一些常用的函数