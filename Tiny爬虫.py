#################################库的导入####################################
import requests  #获取网页
from bs4 import BeautifulSoup #处理网页
import jieba  #处理网页汉字，分词
import sqlite3  #数据库
import xpinyin  #获取拼音
import os  #文件处理
from os import path  #路径处理
from langconv import * #繁体转换简体
import re  #正则表达式处理字符串
import chardet  #检测网页编码
import tkinter  #UGI
import  tkinter.messagebox  #提示框
import time  #获取本地时间

#####################################全局变量######################################
if os.path.exists("C:\\Users\\DELL\\Desktop\\python final project\\database"):
    dataBase_dir = "C:\\Users\\DELL\\Desktop\\python final project\\database"  #关键词和url数据库文件路径
    already_crawl_dir = "C:\\Users\\DELL\\Desktop\\python final project\\database\\already_crawled.db" #存放已经爬取过的url
else:
    os.makedirs("C:\\Users\\DELL\\Desktop\\python final project\\database")
    dataBase_dir = "C:\\Users\\DELL\\Desktop\\python final project\\database"
    already_crawl_dir = "C:\\Users\\DELL\\Desktop\\python final project\\database\\already_crawled.db"

crawled_table_name = "crawled_table_name"  #已爬取url的表名

#test = 'https://read.qidian.com/chapter/vmoaVaR8umI3v1oFI-DX8Q2/4eKa7xSN7vy2uJcMpdsVgA2'  #小说网站
#test2 = 'http://v.km.com/dongman/447.html'  #其他网站

skip_count = 0  #重复url计数
update_vocabulary_count = 0  #新词汇加入计数
update_urls_count = 0  #新url计数

###################################子函数#######################################
def creat_table(dir,table_name):  # 输入表名和数据库文件路径，创建新表（不判断表是否存在）
    connection = sqlite3.connect(dir)  # 连接到数据库
    cur = connection.cursor()  # 创建该数据库的游标

    sql = "CREATE TABLE " + table_name + "(url TEXT)"  # 动态创建表

    cur.execute(sql)  # 执行sql语句
    connection.commit()
    connection.close()

def add_url(dir,table_name,url):  #输入路径和一个表名，在这个表下添加url
    connection = sqlite3.connect(dir)
    cur = connection.cursor()

    sql = "INSERT INTO " + table_name + " VALUES" + '("' + url + '")'

    cur.execute(sql)
    connection.commit()
    connection.close()

def get_data(dir,table_name):  #输入路径和表名，返回该表下所有的url
    connection = sqlite3.connect(dir)
    cur = connection.cursor()
    sql = "SELECT * FROM " + table_name + " ORDER BY url"
    urls = cur.execute(sql)

    outlist = {}
    for ele in urls:  #对游标迭代得到关于数据的字典
        outlist.update({ele[0]:''})

    connection.close()

    return outlist

def get_database_name(s):  #输入一个词，返回对应的数据库绝对路径
    a = xpinyin.Pinyin()
    firt_letter = a.get_pinyin(s,'-')[0]

    dataBaseName = "dataBase_" + firt_letter + '.db'
    return os.path.join(dataBase_dir,dataBaseName)

def init_table_database():  #初始化已爬数据库，创建url的表
    try:
        creat_table(already_crawl_dir,crawled_table_name)  #尝试在已爬取url数据库中创建url表
    except:
        pass

    note.config(state='normal')  #提示已爬url成功载入
    note.insert('insert', 'The URL list has been successfully loaded.')
    note.config(state='disabled')

def tradition_to_simple(sentence):# 将繁体转换成简体
    sentence = Converter('zh-hans').convert(sentence)
    return sentence

def get_the_longest(s):  #输入字符串，输出字符串中最长的一行,用于起点网小说爬取判定正文
    s = s.split('\r')

    i = 0
    longest = 0

    while i < len(s):
        if longest < len(s[i]):
            buf = s[i]
            longest = len(s[i])
        i += 1

    buf = buf.split('\n')
    i = 0
    longest = 0

    while i < len(buf):
        if longest < len(buf[i]):
            out = buf[i]
            longest = len(buf[i])
        i += 1

    return out

def get_all_table(sqlname):  #输入数据库名字，获取该数据库的表
    sqldir = path.join(dataBase_dir,sqlname)

    if path.exists(sqldir):  #文件存在
        connection = sqlite3.connect(sqldir)
        c = connection.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
        tab_name = c.fetchall()
        if tab_name:
            tab_name = [ele[0] for ele in tab_name]
        else:
            tab_name = []
        connection.close()
        return tab_name
    else:
        return None

def get_all_url(table):  #输入表名，输出该表下的url
    filelist = os.listdir(dataBase_dir)  #获取所有的数据库名称

    for file in filelist:
        databaseDir = path.join(dataBase_dir,file)

        connection = sqlite3.connect(databaseDir)
        c = connection.cursor()

        sql = 'SELECT * FROM ' + table  #得到动态命令
        try:
            c.execute(sql)  #执行命令

            urls = [ele[0] for ele in c]
            connection.close()
            return urls
        except:
            continue  #此数据库没有此关键词，进行下一个数据库查找
    return None  #所有数据库都没有这个关键词

def get_time():#联网获取时间
    t = time.ctime()

    reg = r'(?<= )\d{1,2}:\d{1,2}:\d{1,2}'
    pattern = re.compile(reg)
    t = re.search(pattern, t).group(0)

    return t

################################类的定义##########################################
class processUrl():  #定义类，属性url，包含网页相关的方法
    def __init__(self,URL):
        self.url = URL  #url
        self.state = None  #状态码
        self.text = self.get_page()  #源代码

    def get_page(self):  #获取页面
        try:
            #伪装成浏览器
            head = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.118 Safari/537.36'}
            r = requests.get(self.url,timeout = 5,headers = head,verify=False)

            bytes = r.content  #获取网页的比特流形式
            encode_way = chardet.detect(bytes)['encoding']  # 获取编码方式

            r.encoding = encode_way  #以该方式编码
            self.text = r.text  #获取网页的str类型的文本
            self.state = r.status_code  #获取响应状态码
            return r.text

        except:
            note.config(state='normal')
            note.insert('insert', '\n-->Can not connect to the server or error url!    ' + get_time())
            note.config(state='disabled')
            self.text = None

    def get_urls(self):  #获取页面中的超链接
        reg = r'(?<=<a href=")https*.+?(?=")'
        pattern1 = re.compile(reg)
        try:
            urllist = pattern1.findall(self.text)
            return urllist
        except:
            return []  #找不到任何超链接，返回空列表

    def get_articl(self):  #从源代码筛选出汉字
        if self.text:
            chars =  "".join(ele  for ele in self.text if '\u4e00' <= ele <= '\u9fff')
            return ''.join(tradition_to_simple(c) for c in chars)  #化繁为简
        else:
            return ''

    def get_title(self):  #获取网页标题
        try:
            soup = BeautifulSoup(self.text,'html.parser')
        except:
            return
        title =  soup.find_all("title")
        title = str(title[0])
        title = title.replace(' ','')
        title = title.replace('\n','')

        reg = r'(?<=>).+?(?=<)'
        pattern = re.compile(reg)

        out = pattern.findall(title)
        if out is []:
            return []
        else:
            return out[0]

    def get_and_separate(self):  #获取源代码汉字，分词，返回关键词列表
        outlist = {}

        if self.get_articl():  #如果源代码不为空
            out = jieba.cut(self.get_articl())
            out = list(out)

            for ele in out:
                if ele not in outlist:
                    outlist.update({ele:''})

            return list(ele for ele in outlist)
        else:
            return []

    def crawl_web(self):  #获取源代码中汉字，分词后，将其中不重复关键词存入数据库。并将该网页url存到包含这个网页的关键词中
        global skip_count  #声明全局变量
        global update_vocabulary_count
        global update_urls_count

        keywords = self.get_and_separate()  #获取该网页关键词列表

        if keywords:  #关键词列表不为空
            for keyword in keywords:  #对于每一个关键词，在对应的关键词数据库进行操作
                dataBasePath = get_database_name(keyword)  #获取对应数据库的绝对路径

                try:  #尝试在这个数据库中新建表（新关键词）
                        creat_table(dataBasePath,keyword)
                        update_vocabulary_count += 1
                except:
                    pass

                urllist = get_data(dataBasePath,keyword)  #获取当前关键词下的的所有url
                if keyword not in urllist:  #在url字段里查找是该网页否已存在，如果不存在
                    add_url(dataBasePath,keyword,self.url)  #不存在，将网页存入url字段

            add_url(already_crawl_dir,crawled_table_name,self.url)  #将该网页加入到已爬取数据库
            update_urls_count += 1
        else:
            return

class Novel(processUrl):  #起点小说网的小说爬取类，继承上一个网页爬取类
    def __init__(self,url):
        super().__init__(url)  #给processUrl类传递初始化参数

    def get_Novel(self):  #特异爬取：起点小说网中小说正文获取
        if self.text:
            soup = BeautifulSoup(self.text, features="lxml").text  #建立soup对象，对源代码获取utf-8编码的字符串
            return get_the_longest(soup)  #返回小说内容
        else:
            return None

    def get_novel_details(self):  #获取本章小说的书名，章节和题目
        title = self.get_title()  #获取小说网页的标题，从标题中筛选各数据

        reg_name = r'[^_]+?(?=_)'
        reg_chapter = r'(?<=_).+?章'
        reg_tit = r'(?<=章).+?(?=_)'

        pattern_name = re.compile(reg_name)
        pattern_chapter = re.compile(reg_chapter)
        patter_tit = re.compile(reg_tit)

        try:
            name = re.search(pattern_name,title).group(0)
        except:
            name = ''
        try:
            chapter = re.search(pattern_chapter,title).group(0)
        except:
            chapter = ''
        try:
            tit = re.search(patter_tit,title).group(0)
        except:
            tit = ''

        return (name,chapter,tit)

class component():
    def __init__(self,parent):
        self.parent = parent

    def entry(self,**data):  #输入框
        for key,value in data.items():
            setattr(self,key,value)

        entry = tkinter.Entry(self.parent,show = self.show,bd = self.bd, width = self.width)  # 网址输入框
        entry.place(x = self.x, y = self.y)  # 输入框
        return entry

    def button(self,**data):  #创建按钮方法
        for key,value in data.items():
            setattr(self,key,value)

        if hasattr(self,'bg'):
            but = tkinter.Button(self.parent,text = self.text,width = self.width,height = self.height,command = self.command,bg = self.bg)
        else:
            but = tkinter.Button(self.parent, text = self.text, width = self.width, height = self.height,command = self.command)
        but.place(x = self.x,y = self.y)
        return but

    def lable(self,**data):  #创建标签方法
        for key,value in data.items():
            setattr(self,key,value)

        notelabel = tkinter.Label(self.parent,text = self.text)
        notelabel.place(x = self.x,y = self.y)
        return notelabel

    def textout(self,**data):  #创建输出框方法
        for key,value in data.items():
            setattr(self,key,value)

        if hasattr(self,'yscrollcommand'):
            out = tkinter.Text(self.parent,width = self.width,height = self.height,yscrollcommand = self.yscrollcommand)
        else:
            out = tkinter.Text(self.parent,width=self.width,height=self.height)
        out.place(x = self.x,y = self.y)
        out.config(state = 'disabled')
        return out

    def scrollbar(self,**data):  #创建滚动条方法
        for key,value in data.items():
            setattr(self,key,value)

        cro = tkinter.Scrollbar(self.parent)
        cro.pack(side = self.side,fill = self.fill)
        return cro

################################界面按钮回调函数##########################################
def crawl_webs_depth():  # 指定爬取的深度，爬取网页并保存在数据库
    global skip_count
    global update_vocabulary_count
    global update_urls_count

    source_url = url_entry.get()  #获取输入框的url
    depth = depth_entry.get()  #获取输入框的爬取深度

    if source_url == ''or not depth.isdigit():  #初步判断输入数据的正确性,不正确则退出此函数
        note.config(state = 'normal')
        note.insert('insert','\n-->Please entry the reasonable url and depth!    ' + get_time())
        note.yview_moveto(1)
        note.config(state = 'disabled')
        return
    else:
        url_pro = processUrl(source_url)  # 实例化对象
        if url_pro.state == None:
            return

    note.config(state='normal')
    note.insert('insert', '\n-->Crawling,please wait...    ' + get_time())
    note.yview_moveto(1)
    note.config(state='disabled')

    crawled_urls = get_data(already_crawl_dir, crawled_table_name)  # 获取数据库中已爬取url为字典


    stateCode.config(state = 'normal')  #显示状态码
    stateCode.delete(0.0,'end')
    stateCode.insert('insert',url_pro.state)
    stateCode.config(state = 'disabled')

    if source_url not in crawled_urls:  # 如果从来没有爬取过该源网页
        url_pro.crawl_web()  # 爬取源网页

    g_last = url_pro.get_urls()  # 第一代url

    g_next = []  #下一代url
    crawled = []  #运行此次函数的时候，缓存已爬取过的url

    while int(depth) > 0:
        depth -= 1

        for url in g_last:  #对第一代url列表每一个元素，创建对象进行爬取，更新数据库
            if url not in crawled: #如在本次爬取中没有爬取过该网站
                if url not in crawled_urls:  # 如果从来没有爬取过该网站

                    urlobj = processUrl(url)  #实例化对象
                    urlobj.crawl_web()  #爬取目前循环的网站

                    g_next += urlobj.get_urls()  #将新的url加入到下一代url列表中
                    crawled.append(url)

                else:skip_count += 1

            else:
                skip_count += 1

        g_last = g_next
        g_next = []

    note.config(state='normal')
    note.insert('insert', '\n-->Already skipped {} urls which were crawled before.'.format(skip_count))
    note.insert('insert','\n-->{} vocabulary,{} urls were updated.'.format(update_vocabulary_count,update_urls_count))
    note.insert('insert','\n-->Crawl finished.    ' + get_time())
    note.yview_moveto(1)
    url_entry.delete(0, "end")  # 清空输入框
    depth_entry.delete(0, 'end')
    note.config(state='disabled')

    skip_count = 0  #各项计数清零
    update_vocabulary_count = 0
    update_urls_count = 0

def crawl_novel():  #点击按钮，得到小说内容
    url = url_entry.get()  #从输入框获取url
    if url == '':
        return
    obj = Novel(url)  #实例化对象

    if obj.state == 200:  #代表已经成功获取了源代码
        stateCode.config(state='normal')  #显示状态码
        stateCode.delete(0.0, 'end')
        stateCode.insert('insert',obj.state)
        stateCode.config(state='disabled')

        out = obj.get_Novel()  #获取小说正文
        (a,b,c) = obj.get_novel_details()
        name = "<<" + a + ">>"

        output.config(state = 'normal')
        output.delete(0.0,'end')  # 清空屏幕
        output.insert('insert',48*' ' + name + '\n')
        output.insert('insert',40*' ' + b + '   ' + c )
        output.insert('insert','\n' + out)
        output.config(state='disabled')

def getpage():
    url = url_entry.get()
    if url == '':
        return
    obj = processUrl(url)

    if obj.state == 200:
        stateCode.config(state='normal')  #显示状态码
        stateCode.delete(0.0, 'end')
        stateCode.insert('insert', obj.state)
        stateCode.config(state='disabled')

        output.config(state='normal')
        output.delete(0.0,'end')  # 清空屏幕
        output.insert('insert',obj.text)
        output.config(state='disabled')

def getkeywords(): #按下按钮后显示输入的数据库的所有表
    flag = 0
    word = url_entry.get()  #获取输入框的文件名
    if word == '':
        flag = 1
        return

    if word.find('.db') == -1:#没有输入后缀,自动补上后缀
        word += '.db'

    keywords = get_all_table(word)

    if keywords == None and flag == 0:#没有此数据库
        note.config(state = 'normal')  #提示没有该数据库
        note.insert('insert',"-->\nThis data base doesn't exist.    " + get_time())
        note.yview_moveto(1)
        note.config(state = 'disabled')

    elif keywords == [] and flag == 0:  #没有任何表,即没有关键词
        note.config(state='normal')
        note.insert('insert', "\n-->This data base doesn't have any table.    " + get_time())
        note.yview_moveto(1)
        note.config(state='disabled')
        url_entry.delete(0, 'end')

    else:
        if keywords:
            s = ''.join(ele + ',' for ele in keywords)
        else:
            s = ''
        output.config(state='normal')
        output.delete(0.0,'end')
        output.insert('insert',s)
        output.config(state='disabled')
        url_entry.delete(0,'end')

def geturls():  #输入关键词，输出关键词下的url
    keyword = url_entry.get()  #从输入框获取关键词

    if keyword == '':
        return

    urllist = get_all_url(keyword)
    if urllist:
        urllist = [url + '\n' for url in urllist]  #每一个url后接\n，以便输出框观察
        urllist = ''.join(url for url in urllist)  #url列表转换为字符串

        output.config(state='normal')
        output.delete(0.0, 'end')
        output.insert('insert', urllist)
        output.config(state='disabled')

    else:
        note.config(state = 'normal')
        note.insert('insert','\n-->No such keyword.    ' + get_time())
        note.yview_moveto(1)
        note.config(state = 'disabled')

def clear_all():  #清除全部框
    stateCode.config(state = 'normal')
    stateCode.delete(0.0,'end')
    stateCode.config(state='disabled')

    note.config(state = 'normal')
    note.delete(0.0,'end')
    note.config(state='disabled')

    output.config(state = 'normal')
    output.delete(0.0,'end')
    output.config(state='disabled')

    url_entry.delete(0, 'end')
    depth_entry.delete(0, 'end')

def delete_database():  #清除所有数据库
    result = tkinter.messagebox.askyesno('Warning!', 'Are you sure you want to clear all databases?')
    if result:
        filelist = os.listdir(dataBase_dir)

        if filelist == []:  #没有任何数据库
            note.config(state='normal')
            note.insert('insert', "\n-->There's no database file can be deleted.    " + get_time())
            note.yview_moveto(1)
            note.config(state='disabled')
            return

        for file in filelist:
            if file[-2:len(file)] == 'db':  #判断是否是数据库文件
                database_path = path.join(dataBase_dir,file)
                os.remove(database_path)

        note.config(state = 'normal')
        note.insert('insert','\n-->Database has been cleared    ' + get_time())
        note.yview_moveto(1)
        note.config(state = 'disabled')
        init_table_database()

def clear_entry():  #清空所有输入框
    url_entry.delete(0,'end')
    depth_entry.delete(0,'end')

#####################################主函数#######################################
if __name__=='__main__':
    #//////////////////窗口////////////////#
    root = tkinter.Tk()  # 创建窗口
    root.title('Tiny爬虫')  # 窗口标题
    root.geometry('800x550')  # 窗口大小
    root.resizable(width=False, height=False)  # 限制拉伸

    #////////////////窗口各组件//////////////#
    components = component(root)  #实例化组件类

    output = components.textout(width=108, height=20, x=20, y=70)  # 输出文本框
    scrollbar = components.scrollbar(side='right',command =  output.yview,fill = 'y')  # 输出框的滚动条,指明了滚动条的回调函数
    scrollbar.config(command=output.yview)  # 指明滚动条的回调函数
    output.config(yscrollcommand=scrollbar.set)  # 指明移动焦点时的回调函数
    url_entry = components.entry(show = None,bd = 3,width = 80,x = 20,y = 470)  #创建输入框
    depth_entry = components.entry(show = None,bd = 3,width = 4,x = 600,y = 470)  #创建爬取深度输入框

    button_crawl = components.button(text = 'Crawl',width = 8,height = 1,x = 645,y = 466,command = crawl_webs_depth,bg = 'green')  #创建爬取按钮
    button_clear = components.button(text = 'Clear',width = 8,height = 1,x = 715,y = 466,command = clear_entry,bg = 'green')  #清空按钮
    button_get_articel = components.button(text = 'Crawl Novel',width = 15,height = 1,command = crawl_novel,x = 2,y = 2,bg = 'green')  #获取小说文本按钮
    button_get_page = components.button(text = 'Get Page',width = 15,height = 1,command = getpage,x = 120,y = 2,bg = 'green')  #获取网页源码按钮
    button_get_table = components.button(text = 'Get Keywords',width = 15,height = 1,command = getkeywords,x = 238,y = 2,bg = 'green')  #获取关键词按钮
    button_get_urls = components.button(text = 'Get URLs',width = 15,height = 1,command = geturls,x = 356,y = 2,bg = 'green')  #搜索关键词的url按钮
    button_clear_all = components.button(text = 'Clear All',width = 15,height = 1,command = clear_all,x = 474,y = 2,bg = 'green')  #清除全部信息按钮
    button_delete_database = components.button(text = 'Delete Database',bg = 'red',width = 15,height = 1,command = delete_database,x = 592,y = 2)  #清除数据库按钮
    button_quit = components.button(text = 'Quit',width = 8,height = 1,bg = 'red',command = root.quit,x = 710,y = 2)  #退出按钮

    note_label = components.lable(text = 'Entry',x = 300,y = 495)  #输入的标签
    note_depth = components.lable(text = 'Depth',x = 598,y = 495)  #爬取深度的标签
    note_stateCode = components.lable(text='State Code', x=18, y=45)  # 状态码标签

    note = components.textout(width = 108,height = 7,x = 20,y = 355)  # 提示文本框
    stateCode = components.textout(width = 3,height = 1,x = 90,y = 46)  #状态码显示

    ############################################################################
    init_table_database()
    root.mainloop()