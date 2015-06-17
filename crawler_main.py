"""
crawler study code 

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
    id = r"xxxxxx"
    password = r"xxxxxx"
    
    def __init__(self):
        pass

    def save_file(self, path, str, encoding):
        with codecs.open(path, 'w', encoding)  as fp:
            fp.write(str)
    
    def get_xsrf(self):
        response = requests.get(self.url, headers = self.header)
        text = response.text
        self.save_file("pre_page.htm", text, response.encoding)
        soup = BeautifulSoup(text);
        input_tag = soup.find("input", {"name": "_xsrf"})
        xsrf = input_tag["value"]
        return xsrf
        
    def get_login_page(self, xsrf):
        login_url = self.url + r"login"
        post_dict = {
            'rememberme': 'y',
            'password': self.password,
            'email': self.id,
            '_xsrf':xsrf    
        }
        reponse_login = requests.post(login_url, headers = self.header, data = post_dict)
        self.save_file('login_page.htm', reponse_login.text, reponse_login.encoding)
        self.get_people(reponse_login.text)
        
    def get_people(self, html_text): #打印用户的链接
        soup = BeautifulSoup(html_text)
        for link in soup.find_all("a"):
            try:
                if link["href"].index("http://www.zhihu.com/people/") == 0:
                    print(link["href"])
            except:
                pass
        
    
if __name__ == "__main__":
    z = ZhihuInspect()
    xsrf = z.get_xsrf()
    z.get_login_page(xsrf)
    print("ok\n")
    
    
