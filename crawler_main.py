"""
Zhihu bigdata 

Author: smilexie1113@gmail.com

"""
import requests
import codecs 
from bs4 import BeautifulSoup
from enum import Enum

class DebugLevel(Enum):
    verbose = 1
    warning = 2
    error = 3
    end = 4

my_header = {
        'Connection': 'Keep-Alive',
        'Accept': 'text/html, application/xhtml+xml, */*',
        'Accept-Language': 'zh-CN,zh;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Accept-Encoding': 'gzip,deflate,sdch',
        'Host': 'www.zhihu.com',
        'DNT': '1'
    }

class ZhihuInspect(object):
    
    def __init__(self):
        self.base_url = r"http://www.zhihu.com/"
        self.first_url = r"http://www.zhihu.com/explore"
        self.email = r"xxxxx"
        self.password = r"xxxxx"
        self.debug_level = DebugLevel.end
        self.users = []
        pass

    def debug_print(self, level, log_str):
        if level.value >= self.debug_level.value:
            print(log_str)
        #todo: write log file.
    
    def save_file(self, path, str_content, encoding):
        with codecs.open(path, 'w', encoding)  as fp:
            fp.write(str_content)
            
    def print_all_user(self):
        print("user num: " + str(len(self.users)))
        for user in self.users:
            print(user)
    
    def add_user(self, user):
        for user_node in self.users:
            if user_node.name == user.name:
                user_node.agree_cnt = user.agree_cnt
                user_node.thank_cnt = user.thank_cnt
                break;        
        else:
            self.users.append(user)           
    
    def init_xsrf(self):
        """初始化，获取xsrf"""
        response = requests.get(self.base_url, headers = my_header)
        text = response.text
        self.save_file("pre_page.htm", text, response.encoding)
        soup = BeautifulSoup(text);
        input_tag = soup.find("input", {"name": "_xsrf"})
        xsrf = input_tag["value"]
        self.xsrf = xsrf
        
    def get_login_page(self):
        """获取登录后的界面，需要先运行init_xsrf"""
        login_url = self.base_url + r"login"
        post_dict = {
            'rememberme': 'y',
            'password': self.password,
            'email': self.email,
            '_xsrf':self.xsrf    
        }
        reponse_login = requests.post(login_url, headers = my_header, data = post_dict)
        self.save_file('login_page.htm', reponse_login.text, reponse_login.encoding)
        
    def get_user_url(self, html_text): #获取一个页面中的所有用户链接
        soup = BeautifulSoup(html_text)
        user_url = []
        for a_tag in soup.find_all("a"):
            try:
                if a_tag["href"].find("http://www.zhihu.com/people/") == 0:
                    user_url.append(a_tag["href"])
                elif a_tag["href"].find("/people/") == 0:
                    user_url.append(r"http://www.zhihu.com" + a_tag["href"])
            except KeyError:
                #html页面中 a标签下无href属性，不处理 
                pass
        return user_url
    
    def get_question_url(self, html_text): #获取一个页面中的所有quesion链接
        soup = BeautifulSoup(html_text)
        question_url = []
        for a_tag in soup.find_all("a"):
            try:
                if a_tag["href"].find("/question/") == 0:
                    tmp_url = a_tag["href"]
                    #把/question/31491363/answer/54700182 截取为 /question/31491363
                    url_end = tmp_url.find("/", len("/question/")) #第二个参数为查找的启始下标
                    if url_end > 0:
                        tmp_url = tmp_url[:url_end]
                    question_url.append(r"http://www.zhihu.com" + tmp_url)
            except KeyError:
                #html页面中 a标签下无href属性，不处理 
                pass
        return question_url
    
    def process_question_url(self, urls):
        for question_url in urls:
            text = self.get_page(question_url)
            user_urls = self.get_user_url(text)
            for user_url in user_urls:
                user = ZhihuUser(user_url)
                if user.is_valid():
                    self.add_user(user)    
            return #todo: delete. 测试用，只处理第一个quesion url
            
    def get_first_page(self):
        response = requests.get(self.first_url, headers = my_header)
        text = response.text
        self.save_file("first_page.htm", text, response.encoding)
        return text
    
    def get_page(self, url):
        response = requests.get(self.first_url, headers = my_header)
        #todo: 加一个延时，避免被服务器认为是攻击
        text = response.text
        return text

class ZhihuUser(object):
    extra_info_key = ("education item", "education-extra item", "employment item", \
                      "location item", "position item");
        
    def __init__(self, user_url):
        self.debug_level = DebugLevel.verbose
        self.user_url = user_url
        self.valid = self.parse_user_page()
        if self.valid:
            self.extra_info = {}
            self.parse_extra_info()
    
    def is_valid(self):
        return self.valid
    
    def debug_print(self, level, log_str):
        if level.value >= self.debug_level.value:
            print(log_str)
    
    def save_file(self, path, str_content, encoding):
        with codecs.open(path, 'w', encoding)  as fp:
            fp.write(str_content)
            
    def parse_user_page(self):
        self.debug_print(DebugLevel.verbose, "parse " + self.user_url)
        response = requests.get(self.user_url, headers = my_header) #todo 有些页面发现返回200，但页面是空的, 或是首页
        self.save_file("user_page.htm", response.text, response.encoding)
        self.first_user_page_is_save = True
        soup = BeautifulSoup(response.text)        
        self.soup = soup
        try:
            #class_即是查找class，因为class是保留字，bs框架做了转化
            name_tag = soup.find("span", class_="name")
            name = name_tag.contents[0]
            agree_tag = soup.find("span", class_="zm-profile-header-user-agree") 
            agree_cnt = agree_tag.contents[1].contents[0]
            thank_tag = soup.find("span", class_="zm-profile-header-user-thanks") 
            thank_cnt = thank_tag.contents[1].contents[0]
            self.name = name
            self.thank_cnt = int(thank_cnt)
            self.agree_cnt = int(agree_cnt)
            return True
        except AttributeError:
            self.debug_print(DebugLevel.warning, "fail to parse " + self.user_url)
            return False
    
    def parse_extra_info(self):
        #知乎上的格式类似以下形式：<span class="position item" title="流程设计">
        for key_str in self.extra_info_key:
            tag = self.soup.find("span", class_=key_str)
            if tag is not None:
                self.extra_info[key_str] = tag["title"]
        
        
    def __str__(self):
        #print类的实例打印的字符串
        out_str = "User " + self.name + " agree: " + str(self.agree_cnt) + ", " \
            "thank: " + str(self.thank_cnt)
        for key_str in self.extra_info_key:
            if key_str in self.extra_info:
                out_str += " " + key_str + ": " + self.extra_info[key_str]

        return out_str
    
if __name__ == "__main__":
    z = ZhihuInspect()
    first_page = z.get_first_page()
    question_urls = z.get_question_url(first_page)
    z.process_question_url(question_urls)
    z.print_all_user()
    
    print("ok\n")
    
    
