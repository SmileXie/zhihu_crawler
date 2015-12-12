"""
Zhihu Crawler 
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

class ZhihuCrawler(object):
    
    def __init__(self):
        self._base_url = r"http://www.zhihu.com"
        self._root_topic = r"http://www.zhihu.com/topic/19776749" #知乎的根话题
        self._email = r"xxxxx"
        self._password = r"xxxxx"
        self._debug_level = DebugLevel.verbose
        self._visited_user_url = set() #set 查找元素的时间复杂度是O(1)
        self._visited_topic_url = set() 
        self._visited_answer_url = set()
        self._anonymous_cnt = 0 #精华回答中的匿名个数
        pass
    
    def do_crawler(self):
        self._traverse_topic()
    
    def _debug_print(self, level, log_str):
        if level.value >= self._debug_level.value:
            print("[CRAWLER] " + log_str)
        #todo: write log file.
    
    def _save_file(self, path, str_content, encoding):
        with codecs.open(path, 'w', encoding)  as fp:
            fp.write(str_content)
            
    def _save_user(self, user):
        with open("users_json.txt", "a") as fp:
            json_str = json.dumps(user, default = ZhihuUser.obj_to_dict, ensure_ascii = False, sort_keys = True)
            fp.write(json_str + "\n")
    
    def _save_answer(self, answer):
        with open("answer_json.txt", "a") as fp:
            json_str = json.dumps(answer, default = ZhihuAnswer.obj_to_dict, ensure_ascii = False, sort_keys = True)
            fp.write(json_str + "\n")
            
    def _save_topic(self, topic):
        with open("topic_json.txt", "a") as fp:
            json_str = json.dumps(topic, default = ZhihuTopic.obj_to_dict, ensure_ascii = False, sort_keys = True)
            fp.write(json_str + "\n")
    
    def init_xsrf(self):
        """初始化，获取xsrf"""
        response = requests.get(self._base_url, headers = ZhihuCommon.my_header)
        text = response.text
        self._save_file("pre_page.htm", text, response.encoding)
        soup = BeautifulSoup(text)
        input_tag = soup.find("input", {"name": "_xsrf"})
        xsrf = input_tag["value"]
        self.xsrf = xsrf
        
    def get_login_page(self):
        """获取登录后的界面，需要先运行init_xsrf"""
        login_url = self._base_url + r"/login"
        post_dict = {
            'rememberme': 'y',
            'password': self._password,
            'email': self._email,
            '_xsrf':self.xsrf    
        }
        reponse_login = requests.post(login_url, headers = ZhihuCommon.my_header, data = post_dict)
        self._save_file('login_page.htm', reponse_login.text, reponse_login.encoding)

    def _traverse_topic(self):
        """广度优先遍历话题，解析各子话题"""
        help_q = deque() #广度优先搜索的辅助队列
        
        topic = ZhihuTopic(self._root_topic)
        if topic.is_valid():
            self._visited_topic_url.add(topic.get_url())
            self._save_topic(topic) 
            self._parse_top_answers(topic.get_top_answers())
            help_q.append(topic)
        
        while len(help_q) != 0:
            tmp_topic = help_q.popleft()
            for topic_url in tmp_topic.get_related_topic():
                if topic_url not in self._visited_topic_url:
                    new_topic = ZhihuTopic(topic_url)
                    if not new_topic.is_valid():
                        continue
                
                    self._visited_topic_url.add(new_topic.get_url())
                    self._save_topic(new_topic) 
                    self._parse_top_answers(new_topic.get_top_answers())
                    help_q.append(new_topic)
    
    def _parse_top_answers(self, top_answers):
        for as_url in top_answers:
            answer = ZhihuAnswer(as_url)
            if not answer.is_valid():
                continue
            
            if as_url not in self._visited_answer_url:
                self._visited_answer_url.add(as_url)
                self._save_answer(answer)
            
            if (answer.get_author_url() is not None) and (answer.get_author_url() not in self._visited_user_url):
                author = ZhihuUser(answer.get_author_url())
                if author.is_valid():
                    self._visited_user_url.add(author.get_url())
                    self._save_user(author)
            else:
                self._anonymous_cnt += 1
            
class ZhihuTopic(object):
    def __init__(self, url):
        self._base_url = r"http://www.zhihu.com"
        self._debug_level = DebugLevel.verbose
        self._url = url
        self._related_topic_urls = []
        self._top_answer_urls = []
        self._valid = self._parse_topic()
        if self._valid:
            self._parse_related_topic()
            self._parse_top_answer()
            self._debug_print(DebugLevel.verbose, "find " + str(len(self._top_answer_urls)) + " answers") 
            self._debug_print(DebugLevel.verbose, "parse " + url + ". topic " + self._name + " OK!")
        pass

    def _debug_print(self, level, log_str):
        if level.value >= self._debug_level.value:
            print("[TOPIC] " + log_str)
        #todo: write log file.

    def is_valid(self):
        return self._valid

    def get_url(self):
        return self._url
    
    def get_top_answers(self):
        return self._top_answer_urls
    
    def get_related_topic(self):
        return self._related_topic_urls
    
    @staticmethod
    def obj_to_dict(obj):
        """把ZhihuTopic转成dict数据，用于ZhihuCrawler。save_topic中的json dump"""   
        tmp_dict = {}
        tmp_dict["name"] = obj._name
        tmp_dict["url"] = obj._url
        return tmp_dict


    def _parse_topic(self):
        is_ok = False
        try:
            response = requests.get(self._url, headers = ZhihuCommon.my_header)
            soup = BeautifulSoup(response.text)
            self.soup = soup
            topic_info_tag = soup.find("h1", class_="zm-editable-content")
            self._name = topic_info_tag.contents[0]
            is_ok = True
        except Exception as err:
            self._debug_print(DebugLevel.warning, "exception raised by parsing " \
                             + self._url + " error info: " + err)            
        finally:
            return is_ok
    
    def _parse_related_topic(self):
        """解析父话题或子话题"""
        for a_tag in self.soup.find_all("a", class_="zm-item-tag"):
            if a_tag["href"].find("/topic/") == 0:
                topic_url = self._base_url + a_tag["href"]
                self._related_topic_urls.append(topic_url)

    def _parse_top_answer_one_page(self, page):
        """解析一个精华回答页面，返回值:是否还有下一页"""

        self._debug_print(DebugLevel.verbose, "paser top answer of topic " + self._url + " " + self._name + " page" \
                        + str(page))

        page_url = self._url + r"/top-answers?page=" + str(page) #指定页码
        try:
            response = requests.get(page_url, headers = ZhihuCommon.my_header)
            soup = BeautifulSoup(response.text)
        except:
            self._debug_print(DebugLevel.warning, "fail to get page " \
                         + page_url)  
            return False

        #搜索question的url
        for tag in soup.find_all("div", class_="zm-item-rich-text js-collapse-body"):
            try:
                question_url = self._base_url + tag["data-entry-url"]
                self._top_answer_urls.append(question_url)
            except:
                self._debug_print(DebugLevel.warning, "fail to get question url in " \
                             + self._url + " page" + str(page))        
                continue

        #如果有下一页的链接
        for tag in soup.find_all("a"):
            if tag.contents[0] == "下一页" :
                return True
        
        ZhihuCommon.get_and_save_page(page_url, "last_page_in_topic.html")
        return False
        
    def _parse_top_answer(self):
        """解析精华回答"""
        go_next_page = True #是否解析下一页
        page = 1
        while go_next_page:
            go_next_page = self._parse_top_answer_one_page(page)
            page += 1

class ZhihuAnswer(object):
    
    def __init__(self, url):
        self._base_url = r"http://www.zhihu.com"
        self._debug_level = DebugLevel.verbose
        self._url = url
        self._valid = self._parse_answer()
    
    def is_valid(self):
        return self._valid;
    
    def get_author_url(self):
        return self._author_url
    
    def get_author_name(self):
        return self._author_name;
    
    def _debug_print(self, level, log_str):
        if level.value >= self._debug_level.value:
            print("[ANSWER] " + log_str)
    
    def _parse_answer(self):
        is_ok = False
        try:
            response = requests.get(self._url, headers = ZhihuCommon.my_header)
            soup = BeautifulSoup(response.text)        
            self.soup = soup
            
            #<div id="zh-question-title" data-editable="false">
            #    <h2 class="zm-item-title zm-editable-content">            
            #        <a href="/question/20296247">数学里的 e 为什么叫做自然底数？是不是自然界里什么东西恰好是 e？</a>            
            #    </h2>
            #</div>
            
            title_tag = soup.find("div", id="zh-question-title")
            a_tag = title_tag.find("a")
            self._question = a_tag.contents[0]
            self._question_url = self._base_url + a_tag["href"]
            

            #<div class="answer-head">
            #   <a class="author-link" data-tip="p$t$andiely921" href="/people/andiely921">鲁医生</a><span class="sep">
            #   或
            #   <div class="zm-item-answer-author-info">
            #       <span class="name">匿名用户</span>
            #   </div>
            #   <div class="zm-item-vote-info " data-votecount="23730">
            # ...
            head_as_tag = soup.find("div", class_="answer-head");
            vote_tag = head_as_tag.find("div", class_="zm-item-vote-info ");
            self._votecount = int(vote_tag["data-votecount"])  

            author_tag = head_as_tag.find("a", class_ = "author-link")
            if author_tag is None:
                #"匿名用户"等，无author-link
                author_tag = head_as_tag.find("div", class_="zm-item-answer-author-info");
                author_name_tag = author_tag.find("span", class_="name")
                self._author_name = author_name_tag.contents[0]
                self._author_url = None
            else:
                self._author_name = author_tag.contents[0]
                self._author_url = self._base_url + author_tag["href"]

            self._debug_print(DebugLevel.verbose, "parse " + self._url  + " ok." + " " + self._question + "vote:" \
                + str(self._votecount) + " author:" + self._author_name)
                
            is_ok = True
        except Exception as e:
            time.sleep(10)
            self._debug_print(DebugLevel.warning, "fail to parse " + self._url + "ErrInfo: " + str(e))
            ZhihuCommon.get_and_save_page(self._url, "Fail_answer.html")
        return is_ok
    
    @staticmethod
    def obj_to_dict(obj):
        """把ZhihuAnswer转成dict数据，用于ZhihuCrawler。save_answer中的json dump"""   
        tmp_dict = {}
        tmp_dict["question"] = obj._question
        tmp_dict["url"] = obj._url
        tmp_dict["author"] = obj._author_name
        tmp_dict["votecount"] = obj._votecount;
        
        return tmp_dict
    
class ZhihuUser(object):
    _extra_info_key = ("education item", "education-extra item", "employment item", \
                      "location item", "position item");
        
    def __init__(self, user_url):
        self._debug_level = DebugLevel.verbose
        self._user_url = user_url
        self._valid = self._parse_user_page()
        if self._valid:            
            self.parse_extra_info()
    
    def is_valid(self):
        return self._valid
    
    def get_url(self):
        return self._user_url
    
    def _debug_print(self, level, log_str):
        if level.value >= self._debug_level.value:
            print("[USER] " + log_str)
    
    def _save_file(self, path, str_content, encoding):
        with codecs.open(path, 'w', encoding)  as fp:
            fp.write(str_content)
    
    @staticmethod
    def obj_to_dict(obj):
        """把ZhihuUser转成dict数据，用于ZhihuCrawler。save_user中的json dump"""   
        tmp_dict = {}
        tmp_dict["name"] = obj._name
        tmp_dict["url"] = obj._user_url
        tmp_dict["thank_cnt"] = obj._thank_cnt
        tmp_dict["agree_cnt"] = obj._agree_cnt
        tmp_dict["is_male"] = obj._gender_is_male
        for key_str in ZhihuUser._extra_info_key:
            if key_str in obj._extra_info:
                tmp_dict[key_str] = obj._extra_info[key_str]
            else:
                tmp_dict[key_str] = ""
            
        return tmp_dict 
                
    def _parse_user_page(self):        
        try:
            response = requests.get(self._user_url, headers = ZhihuCommon.my_header)
            #self._save_file("user_page.htm", response.text, response.encoding)
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
                self._gender_is_male = False
            else:
                self._gender_is_male = True
            self._name = name
            self._thank_cnt = int(thank_cnt)
            self._agree_cnt = int(agree_cnt)
            is_ok = True
            self._debug_print(DebugLevel.verbose, "parse " + self._user_url + " ok. " + "name:" + self._name)
        except Exception as e:
            self._debug_print(DebugLevel.warning, "some exception raised by parsing " \
                             + self._user_url + "ErrInfo: " + str(e))
            is_ok = False
        finally:
            return is_ok
    
    def parse_extra_info(self):
        #<span class="position item" title="流程设计">
        self._extra_info = {}
        for key_str in self._extra_info_key:
            tag = self.soup.find("span", class_=key_str)
            if tag is not None:
                self._extra_info[key_str] = tag["title"]
        
        
    def __str__(self):
        #print类的实例打印的字符串
        out_str = "User " + self._name + " agree: " + str(self._agree_cnt) + ", " \
            "thank: " + str(self._thank_cnt) 
        if self._gender_is_male:
            out_str += " male "
        else:
            out_str += " female "
        for key_str in self._extra_info_key:
            if key_str in self._extra_info:
                out_str += " " + key_str + ": " + self._extra_info[key_str]

        return out_str


class ZhihuCommon(object):
    """ZhihuCrawler, ZhihuTopic, ZhihuUser三个类的共用代码, 包含一些服务于debug的函数, 共用的网页获取函数, 等。"""
    
    my_header = {
        'Connection': 'Keep-Alive',
        'Accept': 'text/html, application/xhtml+xml, */*',
        'Accept-Language': 'zh-CN,zh;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Accept-Encoding': 'gzip,deflate,sdch',
        'Host': 'www.zhihu.com',
        'DNT': '1'
    }
    
    @staticmethod
    def get_and_save_page(url, path):
        try:
            response = requests.get(url, headers = ZhihuCommon.my_header)
            with codecs.open(path, 'w', response.encoding)  as fp:
                fp.write(response.text)
            return
        except Exception as e:
            print("fail to get " + url + " error info: " + str(e))
            return
        
def main():
    z = ZhihuCrawler()
    z.init_xsrf()
    z.do_crawler()

    print("ok\n")

if __name__ == "__main__":    
    main()
    
