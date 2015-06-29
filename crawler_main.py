"""
Zhihu bigdata 

Author: smilexie1113@gmail.com

"""
import requests
import codecs 
from bs4 import BeautifulSoup

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
    url = r"http://www.zhihu.com/"
    first_url = r"http://www.zhihu.com/explore"
    id = r"xxxxx"
    password = r"xxxxx"
    
    def __init__(self):
        pass

    def save_file(self, path, str_content, encoding):
        with codecs.open(path, 'w', encoding)  as fp:
            fp.write(str_content)
    
    def init_xsrf(self):
        """初始化，获取xsrf"""
        response = requests.get(self.url, headers = self.header)
        text = response.text
        self.save_file("pre_page.htm", text, response.encoding)
        soup = BeautifulSoup(text);
        input_tag = soup.find("input", {"name": "_xsrf"})
        xsrf = input_tag["value"]
        self.xsrf = xsrf
        
    def get_login_page(self):
        """获取登录后的界面，需要先运行init_xsrf"""
        login_url = self.url + r"login"
        post_dict = {
            'rememberme': 'y',
            'password': self.password,
            'email': self.id,
            '_xsrf':self.xsrf    
        }
        reponse_login = requests.post(login_url, headers = self.header, data = post_dict)
        self.save_file('login_page.htm', reponse_login.text, reponse_login.encoding)
        self.get_people(reponse_login.text)
        
    def get_people(self, html_text): #打印用户的链接
        soup = BeautifulSoup(html_text)
        for link in soup.find_all("a"):
            try:
                if link["href"].find("http://www.zhihu.com/people/") == 0:
                    print(link["href"])
            except KeyError:
                #html页面中 a标签下无href属性，不处理 
                pass
    
    def get_first_page(self):
        response = requests.get(self.first_url, headers = self.header)
        text = response.text
        self.save_file("first_page.htm", text, response.encoding)
        self.get_people(text)
        
    
if __name__ == "__main__":
    z = ZhihuInspect()
    z.get_first_page()
    print("ok\n")
    
    
