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

class ZhihuInspect(object):
    header = {
        'Connection': 'Keep-Alive',
        'Accept': 'text/html, application/xhtml+xml, */*',
        'Accept-Language': 'zh-CN,zh;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Accept-Encoding': 'gzip,deflate,sdch',
        'Host': 'www.zhihu.com',
        'DNT': '1'
    }
    base_url = r"http://www.zhihu.com/"
    first_url = r"http://www.zhihu.com/explore"
    email = r"xxxxx"
    password = r"xxxxx"
    debug_level = DebugLevel.verbose
    users = []
    
    def __init__(self):
        pass

    def save_file(self, path, str_content, encoding):
        with codecs.open(path, 'w', encoding)  as fp:
            fp.write(str_content)
    
    def debug_print(self, level, log_str):
        if level.value >= self.debug_level.value:
            print(log_str)
        #todo: write log file.
    
    def print_all_user(self):
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
        response = requests.get(self.base_url, headers = self.header)
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
        reponse_login = requests.post(login_url, headers = self.header, data = post_dict)
        self.save_file('login_page.htm', reponse_login.text, reponse_login.encoding)
        self.get_user_url(reponse_login.text)
        
    def get_user_url(self, html_text): #打印用户的链接
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
    
    def process_user_urls(self, urls):
        for user_url in urls:
            self.parse_user_page(user_url)
    
    def parse_user_page(self, url):
        self.debug_print(DebugLevel.verbose, "parse " + url)
        response = requests.get(url, headers = self.header) #todo 有些页面发现返回200，但页面是空的, 或是首页
        self.save_file("user_page.htm", response.text, response.encoding)
        self.first_user_page_is_save = True
        soup = BeautifulSoup(response.text)        
        
        try:
            #class_即是查找class，因为class是保留字，bs框架做了转化
            name_tag = soup.find("span", class_="name")
            name = name_tag.contents[0]
            agree_tag = soup.find("span", class_="zm-profile-header-user-agree") 
            agree_cnt = agree_tag.contents[1].contents[0]
            thank_tag = soup.find("span", class_="zm-profile-header-user-thanks") 
            thank_cnt = thank_tag.contents[1].contents[0]
            user = ZhihuUser(name, int(agree_cnt), int(thank_cnt))
            self.add_user(user)
        except AttributeError:
            self.debug_print(DebugLevel.warning, "fail to parse " + url)
            
    def get_first_page(self):
        response = requests.get(self.first_url, headers = self.header)
        text = response.text
        self.save_file("first_page.htm", text, response.encoding)
        return text

class ZhihuUser(object):
    debug_level = DebugLevel.verbose
        
    def __init__(self, name, agree_cnt, thank_cnt):
        self.debug_print(DebugLevel.verbose, "new user:" + name + " agree:" + 
                         str(agree_cnt) + " thank:" + str(thank_cnt))
        self.name = name
        self.agree_cnt = agree_cnt
        self.thank_cnt = thank_cnt
        pass
    
    def debug_print(self, level, log_str):
        if level.value >= self.debug_level.value:
            print(log_str)
    
    def __str__(self):
        #print类的实例打印的字符串
        return "User " + self.name + " agree: " + str(self.agree_cnt) + ", " \
            "thank: " + str(self.thank_cnt)
    
if __name__ == "__main__":
    z = ZhihuInspect()
    first_page = z.get_first_page()
    user_urls = z.get_user_url(first_page)
    z.process_user_urls(user_urls)
    z.print_all_user()
    
    print("ok\n")
    
    
