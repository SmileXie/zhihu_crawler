"""
Zhihu bigdata 

Author: smilexie1113@gmail.com

"""
import requests
import codecs 
import json
import time
from collections import deque
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

def user_obj_to_dict(obj):
    """把ZhihuUser转成dict数据，用于ZhihuInspect。save_user中的json dump"""   
    tmp_dict = {}
    tmp_dict["name"] = obj.name
    tmp_dict["url"] = obj.user_url
    tmp_dict["thank_cnt"] = obj.thank_cnt
    tmp_dict["agree_cnt"] = obj.agree_cnt
    tmp_dict["is_male"] = obj.gender_is_male
    for key_str in ZhihuUser.extra_info_key:
        if key_str in obj.extra_info:
            tmp_dict[key_str] = obj.extra_info[key_str]
        else:
            tmp_dict[key_str] = ""
        
    return tmp_dict

def topic_obj_to_dict(obj):
    """把ZhihuTopic转成dict数据，用于ZhihuInspect。save_topic中的json dump"""   
    tmp_dict = {}
    tmp_dict["name"] = obj.name
    tmp_dict["url"] = obj.url
    return tmp_dict
    
class ZhihuInspect(object):
    
    def __init__(self):
        self.base_url = r"http://www.zhihu.com"
        self.topic_square_url = r"http://www.zhihu.com/topics"
        self.root_topic = r"http://www.zhihu.com/topic/19776749" #知乎的根话题
        self.first_url = self.topic_square_url
        self.email = r"xxxxx"
        self.password = r"xxxxx"
        self.debug_level = DebugLevel.verbose
        self.visited_user_url = set() #set 查找元素的时间复杂度是O(1)
        self.visited_topic_url = set() #set 查找元素的时间复杂度是O(1)
        pass
    
    def do_crawler(self):
        self.__traverse_topic()
    
    def debug_print(self, level, log_str):
        if level.value >= self.debug_level.value:
            print(log_str)
        #todo: write log file.
    
    def save_file(self, path, str_content, encoding):
        with codecs.open(path, 'w', encoding)  as fp:
            fp.write(str_content)
            
    def save_user(self, user):
        with open("users_json.txt", "a") as fp:
            json_str = json.dumps(user, default = user_obj_to_dict, ensure_ascii = False, sort_keys = True)
            fp.write(json_str + "\n")
    
    def add_user(self, user):
        if user.get_url() in self.visited_user_url: #set 查找元素的时间复杂度是O(1)
            return False     
        else:
            self.visited_user_url.add(user.get_url())
            return True

    def __save_topic(self, topic):
        with open("topic_json.txt", "a") as fp:
            json_str = json.dumps(topic, default = topic_obj_to_dict, ensure_ascii = False, sort_keys = True)
            fp.write(json_str + "\n")
    
    def init_xsrf(self):
        """初始化，获取xsrf"""
        response = requests.get(self.base_url, headers = my_header)
        text = response.text
        self.save_file("pre_page.htm", text, response.encoding)
        soup = BeautifulSoup(text)
        input_tag = soup.find("input", {"name": "_xsrf"})
        xsrf = input_tag["value"]
        self.xsrf = xsrf
        
    def get_login_page(self):
        """获取登录后的界面，需要先运行init_xsrf"""
        login_url = self.base_url + r"/login"
        post_dict = {
            'rememberme': 'y',
            'password': self.password,
            'email': self.email,
            '_xsrf':self.xsrf    
        }
        reponse_login = requests.post(login_url, headers = my_header, data = post_dict)
        self.save_file('login_page.htm', reponse_login.text, reponse_login.encoding)

    def __traverse_topic(self):
        """遍历话题，解析各子话题"""
        help_q = deque() #广度优先搜索的辅助队列
        
        topic = ZhihuTopic(self.root_topic)
        if topic.is_valid():
            self.visited_topic_url.add(topic.get_url())
            self.__save_topic(topic) 
            self.__parse_top_answers(topic.get_top_answers())
            help_q.append(topic)
        
        while len(help_q) != 0:
            tmp_topic = help_q.popleft()
            for topic_url in tmp_topic.get_related_topic():
                if topic_url not in self.visited_topic_url:
                    new_topic = ZhihuTopic(topic_url)
                    if new_topic.is_valid():
                        self.visited_topic_url.add(new_topic.get_url())
                        self.__save_topic(new_topic) 
                        self.__parse_top_answers(new_topic.get_top_answers())
                        help_q.append(new_topic)
    
    def __parse_top_answers(self, top_answers):
        for as_url in top_answers:
            answer = ZhihuAnswer(as_url)
            #todo 记录answer
                   
    def get_user_url(self, url):
        """获一个页面中的所有用户链接"""
        user_url = set()
        html_text = self.get_page(url)  
        soup = BeautifulSoup(html_text)
        
        for a_tag in soup.find_all("a"):
            try:
                if a_tag["href"].find("http://www.zhihu.com/people/") == 0:
                    user_url.add(a_tag["href"])
                elif a_tag["href"].find("/people/") == 0:
                    user_url.add(r"http://www.zhihu.com" + a_tag["href"])
            except KeyError:
                #html页面中 a标签下无href属性，不处理 
                pass
        return user_url
    
    def get_question_url(self, url):
        """获取一个页面中的所有quesion链接"""
        html_text = self.get_page(url)
        soup = BeautifulSoup(html_text)
        question_url = set()
        for a_tag in soup.find_all("a"):
            try:
                if a_tag["href"].find("/question/") == 0:
                    tmp_url = a_tag["href"]
                    #把/question/31491363/answer/54700182 截取为 /question/31491363
                    url_end = tmp_url.find("/", len("/question/")) #第二个参数为查找的启始下标
                    if url_end > 0:
                        tmp_url = tmp_url[:url_end]
                    question_url.add(r"http://www.zhihu.com" + tmp_url)
            except KeyError:
                #html页面中 a标签下无href属性，不处理 
                pass
        return question_url
    
    def process_question_url(self, urls):
        for question_url in urls:
            user_urls = self.get_user_url(question_url)
            for user_url in user_urls:
                time.sleep(0.5) #延迟0.5s 避免被智乎认为请求过于频繁
                user = ZhihuUser(user_url)
                if user.is_valid():
                    if self.add_user(user):
                        self.save_user(user) 
            #return #todo: delete. 测试用，只处理第一个quesion url
            
    def get_page(self, url):
        try:
            response = requests.get(url, headers = my_header)
            text = response.text
            return text
        except Exception as e:
            self.debug_print(DebugLevel.warning, "fail to get " \
                             + url + " error info: " + str(e))
            return ""
    
    def get_and_save_page(self, url, path):
        try:
            response = requests.get(url, headers = my_header)
            self.save_file(path, response.text, response.encoding)
            return
        except Exception as e:
            self.debug_print(DebugLevel.warning, "fail to get " \
                             + url + " error info: " + str(e))
            return


class ZhihuTopic(object):
    def __init__(self, url):
        self.base_url = r"http://www.zhihu.com"
        self.debug_level = DebugLevel.verbose
        self.url = url
        self.related_topic_urls = []
        self.__top_answer_urls = []
        self.__valid = self.__parse_topic()
        if self.__valid:
            self.__parse_related_topic()
            self.__parse_top_answer()
            self.debug_print(DebugLevel.verbose, "find " + str(len(self.__top_answer_urls)) + " answers") 
            self.debug_print(DebugLevel.verbose, "parse " + url + ". topic " + self.name + " OK!")
        pass

    def debug_print(self, level, log_str):
        if level.value >= self.debug_level.value:
            print(log_str)
        #todo: write log file.

    def is_valid(self):
        return self.__valid

    def get_url(self):
        return self.url
    
    def get_top_answers(self):
        return self.__top_answer_urls
    
    def get_related_topic(self):
        return self.related_topic_urls
       
    def __parse_topic(self):
        is_ok = False
        try:
            response = requests.get(self.url, headers = my_header)
            soup = BeautifulSoup(response.text)
            self.soup = soup
            topic_info_tag = soup.find("h1", class_="zm-editable-content")
            self.name = topic_info_tag.contents[0]
            is_ok = True
        except Exception as err:
            self.debug_print(DebugLevel.warning, "exception raised by parsing " \
                             + self.url + " error info: " + err)            
        finally:
            return is_ok
    
    def __parse_related_topic(self):
        """解析父话题或子话题"""
        for a_tag in self.soup.find_all("a", class_="zm-item-tag"):
            if a_tag["href"].find("/topic/") == 0:
                topic_url = self.base_url + a_tag["href"]
                self.related_topic_urls.append(topic_url)

    def __parse_top_answer_one_page(self, page):
        """解析一个精华回答页面，返回值:是否还有下一页"""

        self.debug_print(DebugLevel.verbose, "paser top answer of topic " + self.url + " " + self.name + " page" \
                        + str(page))
                             
        if page == 1:
            #第一页无需下载页面，直接用self.soup就好
            soup = self.soup
        else:
            page_url = self.url + r"?page=" + str(page) #指定页码
            try:
                response = requests.get(page_url, headers = my_header)
                soup = BeautifulSoup(response.text)
            except:
                self.debug_print(DebugLevel.warning, "fail to get page" \
                             + page_url)  
                return False

        #搜索question的url
        for tag in soup.find_all("div", class_="zm-item-rich-text js-collapse-body"):
            try:
                question_url = self.base_url + tag["data-entry-url"]
                self.__top_answer_urls.append(question_url)
            except:
                self.debug_print(DebugLevel.warning, "fail to get question url in " \
                             + self.url + " page" + str(page))        
                continue

        #如果有下一页的链接
        for tag in soup.find_all("a"):
            if tag.contents[0] == "下一页" :
                return True

        return False
        
    def __parse_top_answer(self):
        """解析精华回答"""
        go_next_page = True #是否解析下一页
        page = 1
        while go_next_page:
            go_next_page = self.__parse_top_answer_one_page(page)
            page += 1

class ZhihuAnswer(object):
    
    def __init__(self, url):
        self.__base_url = r"http://www.zhihu.com"
        self.__debug_level = DebugLevel.verbose
        self.url = url
        self.__valid = self.__parse_answer()
    
    def __debug_print(self, level, log_str):
        if level.value >= self.__debug_level.value:
            print(log_str)
    
    def __parse_answer(self):
        is_ok = False
        try:
            response = requests.get(self.url, headers = my_header)
            soup = BeautifulSoup(response.text)        
            self.soup = soup
            
            #<div id="zh-question-title" data-editable="false">
            #    <h2 class="zm-item-title zm-editable-content">            
            #        <a href="/question/20296247">数学里的 e 为什么叫做自然底数？是不是自然界里什么东西恰好是 e？</a>            
            #    </h2>
            #</div>
            
            title_tag = soup.find("div", id="zh-question-title")
            a_tag = title_tag.find("a")
            self.question = a_tag.contents[0]
            self.question_url = self.__base_url + a_tag["href"]
            self.__debug_print(DebugLevel.verbose, "parse " + self.url + " " + self.question + " ok.")
            is_ok = True
        except:
            self.__debug_print(DebugLevel.warning, "fail to parse " + self.url)
        return is_ok
           
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
    
    def get_url(self):
        return self.user_url
    
    def debug_print(self, level, log_str):
        if level.value >= self.debug_level.value:
            print(log_str)
    
    def save_file(self, path, str_content, encoding):
        with codecs.open(path, 'w', encoding)  as fp:
            fp.write(str_content)
            
    def parse_user_page(self):
        self.debug_print(DebugLevel.verbose, "parse " + self.user_url)
        try:
            response = requests.get(self.user_url, headers = my_header)
            #self.save_file("user_page.htm", response.text, response.encoding)
            self.first_user_page_is_save = True
            soup = BeautifulSoup(response.text)        
            self.soup = soup
            #class_即是查找class，因为class是保留字，bs框架做了转化
            name_tag = soup.find("span", class_="name")
            name = name_tag.contents[0]
            agree_tag = soup.find("span", class_="zm-profile-header-user-agree") 
            agree_cnt = agree_tag.contents[1].contents[0]
            thank_tag = soup.find("span", class_="zm-profile-header-user-thanks") 
            thank_cnt = thank_tag.contents[1].contents[0]
            gender_tag = soup.find("span", class_="item gender")
            #gender_tag.cont...nts[0]["class"]是一个list，list的每一个元素是字符串
            gender_str = gender_tag.contents[0]["class"][1]
            if gender_str.find("female") > 0:
                self.gender_is_male = False
            else:
                self.gender_is_male = True
            self.name = name
            self.thank_cnt = int(thank_cnt)
            self.agree_cnt = int(agree_cnt)
            is_ok = True
        except AttributeError:
            self.debug_print(DebugLevel.warning, "fail to parse " + self.user_url)
            is_ok = False
        except TimeoutError:
            self.debug_print(DebugLevel.warning, "get " + self.user_url + " timeout.")
            is_ok = False
        except ConnectionError: 
            self.debug_print(DebugLevel.warning, "connect " + self.user_url + " timeout.")
            is_ok = False
        except Exception as e:
            self.debug_print(DebugLevel.warning, "some other exception raised by parsing " \
                             + self.user_url + "error info: " + str(e))
            is_ok = False
        finally:
            return is_ok
    
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
        if self.gender_is_male:
            out_str += " male "
        else:
            out_str += " female "
        for key_str in self.extra_info_key:
            if key_str in self.extra_info:
                out_str += " " + key_str + ": " + self.extra_info[key_str]

        return out_str

def main():
    z = ZhihuInspect()
    z.init_xsrf()
    z.do_crawler()

    print("ok\n")

if __name__ == "__main__":    
    main()
    
