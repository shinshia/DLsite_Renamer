from tkinter import filedialog
from tkinter import messagebox
from lxml import html
import tkinter as tk
import threading
import requests
import time
import re
import os


# 默认命名格式
template = 'RJ号 [社团] 标题 (声优)'

RJ_WEBPATH = 'https://www.dlsite.com/maniax/work/=/product_id/'
RT_WEBPATH = 'https://www.dlsite.com.tw/work/product_id/'
R_COOKIE = {'adultchecked': '1'}

# re.compile()返回一个匹配对象
# ensure path name is exactly RJ###### or RT######
pattern = re.compile("^R[EJT]\d{6}$")
#filter to substitute illegal filenanme characters to " "
filter = re.compile('[\\\/:"*?<>|]+')


# 避免ERROR: Max retries exceeded with url
requests.adapters.DEFAULT_RETRIES = 5 # 增加重连次数
s = requests.session()
s.keep_alive = False # 关闭多余连接
#s.get(url) # 你需要的网址

# 查找母串内所有子串的位置, 查找失败返回-1
def find_all(source,dest):
    length1,length2 = len(source),len(dest)
    dest_list = []
    temp_list = []
    if length1 < length2:
        return -1
    i = 0
    while i <= length1-length2:
        if source[i] == dest[0]:
            dest_list.append(i)
        i += 1
    if dest_list == []:
        return -1
    for x in dest_list:
        #print("Now x is:%d. Slice string is :%s"% (x,repr(source[x:x+length2])),end=" ")
        if source[x:x+length2] != dest:
            #print(" dest != slice")
            temp_list.append(x)
        #else:
            #print(" dest == slice")  
    for x in temp_list:
        dest_list.remove(x)
    return dest_list

# 从文件夹名称中提取r_code
def get_r_code(originalName, matchCode):
    index_list = find_all(originalName, matchCode)
    if index_list == -1:
        return ""
    for i in range(0, len(index_list)):
        r_idx = index_list[i]
        r_code = originalName[r_idx:(r_idx)+8]
        pattern = re.compile("^"+matchCode+"\d{6}$")
        if pattern.match(r_code):
            return r_code.upper()
    return ""        

def match_rj(rj_code):
    # requests库是一个常用于http请求的模块   
    url = RJ_WEBPATH + rj_code
    try:
        r = s.get(url, allow_redirects=False, cookies=R_COOKIE)  # allow_redirects=False 禁止重定向
        # HTTP状态码==200表示请求成功
        if r.status_code != 200:
            #print("    Status code:", r.status_code, "\nurl:", url)
            return r.status_code, "", "", []
            
        # fromstring()在解析xml格式时, 将字符串转换为Element对象, 解析树的根节点
        # 在python中, 对get请求返回的r.content做fromstring()处理, 可以方便进行后续的xpath()定位等
        tree = html.fromstring(r.content)
        title = tree.xpath('//a[@itemprop="url"]/text()')[0]
        circle = tree.xpath('//span[@itemprop="brand" and @class="maker_name"]/*/text()')[0]
        cvList = tree.xpath('//*[@id="work_outline"]/tr/th[contains(text(), "声優")]/../td/a/text()')  
        return 200, title, circle, cvList

    except os.error as err:
        text.insert(tk.END, "**请求超时!\n")
        text.insert(tk.END, "  请检查网络连接\n")
        return "", "", "", []
    
def match_rt(rt_code):
    url = RT_WEBPATH + rt_code
    try:
        r = s.get(url + '.html', allow_redirects=False, cookies=R_COOKIE)
        if r.status_code != 200:
            #print("    Status code:", r.status_code, "\nurl:", url)
            return r.status_code, "", "", []
            
        tree = html.fromstring(r.content)
        title = tree.xpath('//div[@class="works_summary"]/h3/text()')[0]
        circle = tree.xpath('//a[@class="summary_author"]/text()')[0]
        return 200, title, circle, []
        
    except os.error as err:
        text.insert(tk.END, "**请求超时!\n")
        text.insert(tk.END, "  请检查网络连接\n")
        return "", "", "", []

def nameChange():
    # askdirectory()文件对话框, 选择目录, 返回目录名
    path = filedialog.askdirectory()
    if path == "":
        messagebox.showinfo(title="错误", message="请选择路径!" + "\n")
    else:
        btn.config(state=tk.DISABLED)
        btn['text'] = "等待完成"
        text.insert(tk.END, "选择路径: " + path + "\n")
        # os.listdir()返回指定的文件夹包含的文件或文件夹的名字的列表
        files = os.listdir(path)
        for file in files:
            # os.path.isdir()用于判断对象是否为一个目录。
            if os.path.isdir(os.path.join(path,file)):
                # 获取文件夹原始名称
                originalName = file
                # 尝试获取r_code
                r_code = ""
                for matchCode in ['RJ','rj','RT','rt']:
                    r_code = get_r_code(originalName, matchCode)
                    if r_code:
                        break
                # 如果没能提取到r_code
                if r_code == "":
                    continue # 跳过该文件夹
                else:
                    #print('Processing: ' + r_code)
                    text.insert(tk.END, 'Processing: ' + r_code + '\n')
                    if r_code[1] == "J" :
                        r_status, title, circle, cvList = match_rj(r_code)
                    elif r_code[1] == "T" :
                        r_status, title, circle, cvList = match_rt(r_code)
                    # 如果顺利爬取网页信息
                    if r_status == 200 and title and circle:
                        new_name = template.replace("RJ号", r_code)
                        new_name = new_name.replace("标题", title)
                        new_name = new_name.replace("社团", circle)
                        
                        cv = ""
                        if cvList: #如果cvList非空
                            for name in cvList: 
                                cv += " " + name
                            new_name = new_name.replace("声优", cv[1:])
                                        
                        # 将Windows文件名中的非法字符替换   
                        new_name = re.sub(filter, " ", new_name)  # re.sub(pattern, repl, string)
                        # 尝试重命名
                        try:
                            # strip() 去掉字符串两边的空格
                            os.rename(os.path.join(path, originalName), os.path.join(path, new_name.strip()))
                        except os.error as err:
                            text.insert(tk.END, "**重命名失败!\n" )
                            text.insert(tk.END, "  " + os.path.join(path, originalName) + "\n")
                            text.insert(tk.END, "  请检查是否存在重复的名称\n")
                    elif r_status == 404:
                        text.insert(tk.END, "**爬取DLsite过程中出现错误!\n")
                        text.insert(tk.END, "  请检查本作是否已经下架或被收入合集\n")
                    elif r_status != "":
                        text.insert(tk.END, "**爬取DLsite过程中出现错误!\n")
                        text.insert(tk.END, "  网页 URL: " + RJ_WEBPATH + r_code + "\n")
                        text.insert(tk.END, "  HTTP 响应代码: " + str(r_status) + "\n")
                    
                    time.sleep(0.1) #set delay to avoid being blocked from server
        #print("~Finished.")
        text.insert(tk.END, "*******完成!*******\n\n\n\n")
        tk.messagebox.showinfo(title="提示", message="完成!")
        
        btn.config(state=tk.NORMAL)
        btn['text'] = "选择路径"
    
def thread_it(func, *args):
    '''将函数打包进线程'''
    # 创建
    t = threading.Thread(target=func, args=args) 
    # 守护 !!!
    t.setDaemon(True) 
    # 启动
    t.start()
    # 阻塞--卡死界面！
    # t.join()




root = tk.Tk()  # 实例化object，建立窗口root
root.title('DLsite重命名工具 v1.0')  # 给窗口的可视化起名字
root.geometry('300x350')  # 设定窗口的大小(长 * 宽)

text = tk.Text(root)
text.pack()

# 读取配置文件
# os.path.dirname(__file__) 当前脚本所在路径
basedir = os.path.abspath(os.path.dirname(__file__))
try:
    fname = os.path.join(basedir, '配置文件.txt')
    
    with open(fname, 'r', encoding='utf-8') as f:  # 打开配置文件
        lines = f.readlines()  # 读取所有行
        first_line = lines[0]  # 取第一行     
        if first_line != '\n': # 第一行非空
            if ("RJ号" in first_line):
                template = first_line
                text.insert(tk.END, "**使用自定义命名格式:\n")
                text.insert(tk.END, "  " + template + "\n\n")
            else:
                text.insert(tk.END, "**配置文件第一行格式错误\n")
                text.insert(tk.END, "  请修改配置文件\n")
                text.insert(tk.END, "  否则将使用默认命名格式\n\n")
        else:
            text.insert(tk.END, "**配置文件第一行为空!\n")
            text.insert(tk.END, "  请修改配置文件\n")
            text.insert(tk.END, "  否则将使用默认命名格式\n\n")
                                                 
except os.error as err:
    text.insert(tk.END, "**配置文件缺失!\n")
    text.insert(tk.END, "**将使用默认命名格式:\n")
    text.insert(tk.END, "  RJ号 [社团] 标题 (声优)\n")


btn = tk.Button(root, text='选择路径', command=lambda :thread_it(nameChange))
btn.pack()

root.mainloop()