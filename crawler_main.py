"""
crawler study code 

Author: smilexie1113@gmail.com

"""
import requests
from bs4 import BeautifulSoup

def main():
    url = r"http://www.zhihu.com/"
    id = r"xxxxxxxxxx"
    password = r"xxxxxxxxxx"
    
    header = {
        'Connection': 'Keep-Alive',
        'Accept': 'text/html, application/xhtml+xml, */*',
        'Accept-Language': 'en-US,en;q=0.8,zh-Hans-CN;q=0.5,zh-Hans;q=0.3',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Accept-Encoding': 'gzip, deflate',
        'Host': 'www.zhihu.com',
        'DNT': '1'
    }
    
    response = requests.post(url, headers = header)
    text = response.text
    soup = BeautifulSoup(text);
    input_tag = soup.find("input", {"name": "_xsrf"})
    xsrf = input_tag["value"]
    
    url += r"login"
    post_dict = {
        'rememberme': 'y',
        'password': password,
        'email': id,
        '_xsrf':xsrf    
    }
    
    reponse2 = requests.post(url, headers = header, data = post_dict)
    pass
    
if __name__ == "__main__":
    main()