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
        self._base_url = r"https://www.zhihu.com"
        self._phone_num = r""
        self._password = r""
        self._debug_level = DebugLevel.verbose
        self._visited_user_url = set() #set 查找元素的时间复杂度是O(1)
        self._visited_topic_url = set() 
        self._visited_answer_url = set()
        self._anonymous_cnt = 0 #精华回答中的匿名个数
        ZhihuCommon.session_init()
            
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
        with open(ZhihuCommon.user_json_file, "a", encoding = "utf-8") as fp:
            json_str = json.dumps(user, default = ZhihuUser.obj_to_dict, ensure_ascii = False, sort_keys = True)
            fp.write(json_str + "\n")
    
    def _save_answer(self, answer):
        with open(ZhihuCommon.answer_json_file, "a", encoding = "utf-8") as fp:
            json_str = json.dumps(answer, default = ZhihuAnswer.obj_to_dict, ensure_ascii = False, sort_keys = True)
            fp.write(json_str + "\n")
            
    def _save_topic(self, topic):
        with open(ZhihuCommon.topic_json_file, "a", encoding = "utf-8") as fp:
            json_str = json.dumps(topic, default = ZhihuTopic.obj_to_dict, ensure_ascii = False, sort_keys = True)
            fp.write(json_str + "\n")
    
    def init_xsrf(self):
        """初始化，获取xsrf"""
        
        try:
            #下载线_的解释: it has the special meaning that "I don't need this variable, I'm only putting something
            # here because the API/syntax/whatever requires it"
            _, soup = ZhihuCommon.get(self._base_url) 
            input_tag = soup.find("input", {"name": "_xsrf"})
            xsrf = input_tag["value"]
            ZhihuCommon.set_xsrf(xsrf)
        except Exception as e:
            self._debug_print(DebugLevel.error, "fail to init xsrf. " + str(e))
                
        
    def login(self):
        """获取登录后的界面，需要先运行init_xsrf"""
        login_url = self._base_url + r"/login/phone_num"
        post_dict = {
            'rememberme': 'y',
            'password': self._password,
            'phone_num': self._phone_num,
            '_xsrf':ZhihuCommon.get_xsrf() 
        }
        response_login = ZhihuCommon.post(login_url, post_dict)
        # response content: {"r":0, "msg": "\u767b\u9646\u6210\u529f" }
        if response_login.json()["r"] == 0:
            return True
        else:
            return False
        #self._save_file('login_page.htm', reponse_login.text, reponse_login.encoding)
        
    def _traverse_topic(self):
        """广度优先遍历话题，解析各子话题"""
        help_q = deque() #广度优先搜索的辅助队列
        
        topic = ZhihuTopic(ZhihuCommon.root_topic)
        if topic.is_valid():
            self._visited_topic_url.add(topic.get_url())
            self._save_topic(topic) 
            self._parse_top_answers(topic.get_top_answers())
            topic.set_level(1)
            help_q.append(topic)

        
        while len(help_q) != 0:
            parent_topic = help_q.popleft()
            if parent_topic.get_level() >= ZhihuCommon.traversal_level_max:
                #超过遍历深度限制
                break
            
            for topic_id in parent_topic.get_child_topic():
                topic_url = r"https://www.zhihu.com/topic/" + str(topic_id)
                if topic_url not in self._visited_topic_url:
                    new_topic = ZhihuTopic(topic_id)
                    if not new_topic.is_valid():
                        continue
                    new_topic.set_level(parent_topic.get_level() + 1)
                    self._visited_topic_url.add(new_topic.get_url())
                    self._save_topic(new_topic) 
                    self._parse_top_answers(new_topic.get_top_answers())
                    help_q.append(new_topic)
    
    def _parse_top_answers(self, top_answers):
        cnt = 0
        for as_url in top_answers:
            if as_url in self._visited_answer_url:
                continue
            
            answer = ZhihuAnswer(as_url)
            if not answer.is_valid():
                continue

            self._visited_answer_url.add(as_url)
            self._save_answer(answer)
            
            if (answer.get_author_url() is not None) and (answer.get_author_url() not in self._visited_user_url):
                author = ZhihuUser(answer.get_author_url())
                if author.is_valid():
                    self._visited_user_url.add(author.get_url())
                    self._save_user(author)
            else:
                self._anonymous_cnt += 1
                
            cnt += 1
            if ZhihuCommon.debug_fast_crawler and cnt > 10:
                #如果是快速模式，仅解析前十个问题
                break
            
class ZhihuTopic(object):
    def __init__(self, topic_id):
        url = r"https://www.zhihu.com/topic/" + str(topic_id)
        self._base_url = r"https://www.zhihu.com"
        self._topic_id = topic_id
        self._debug_level = DebugLevel.verbose
        self._url = url
        self._child_topic_id = []
        self._top_answer_urls = []
        if topic_id == ZhihuCommon.unclassed_topic: #未分类话题，多是话题别名，不作考虑
            self._valid = False
            self._debug_print(DebugLevel.verbose, "Skip unclassed topic.")
            return        
        self._valid = self._parse_topic()
        if self._valid:
            self._parse_child_topic()
            self._parse_top_answer()
            self._debug_print(DebugLevel.verbose, "find " + str(len(self._top_answer_urls)) + " answers") 
            self._debug_print(DebugLevel.verbose, "parse " + url + ". topic " + self._name + " OK!")

    def _debug_print(self, level, log_str):
        if level.value >= self._debug_level.value:
            print("[TOPIC] " + log_str)
        #todo: write log file.

    def is_valid(self):
        return self._valid
    
    #按深度优先遍历，本话题处于第几个层次
    def set_level(self, level):
        self.level = level
    
    def get_level(self):
        return self.level
        
    def get_url(self):
        return self._url
    
    def get_top_answers(self):
        return self._top_answer_urls
    
    def get_child_topic(self):
        return self._child_topic_id
    
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
            _, soup = ZhihuCommon.get(self._url) 
            self.soup = soup
            topic_info_tag = soup.find("h1", class_="zm-editable-content")
            self._name = topic_info_tag.contents[0]
            is_ok = True
        except Exception as err:
            self._debug_print(DebugLevel.warning, "exception raised by parsing " \
                             + self._url + " error info: " + err)            
        finally:
            return is_ok
    
    def _parse_child_topic(self):        
        
        continue_load = True
        first_query = True
        
        topic_tree_url = r"https://www.zhihu.com/topic/" + str(self._topic_id) + r"/organize/entire"        
        post_dict = {
            '_xsrf':ZhihuCommon.get_xsrf()    
        }
        
        while continue_load:
            if first_query:
                query_url = topic_tree_url
                first_query = False
            else:
                query_url = topic_tree_url + r"?child=" + last_topic + r"&parent=" + parent_topic
            response_login = ZhihuCommon.post(query_url, post_dict) 
            rep_msg = response_login.json()
            
            """ rep_msg structure
            dict: {'msg': [['topic', '「根话题」', '19776749'], 
            [[['topic', '生活、艺术、文化与活动', '19778317'], [[['load', '显示子话题', '', '19778317'], []]]], 
            [['topic', '实体', '19778287'], [[['load', '显示子话题', '', '19778287'], []]]], 
            [['topic', '产业', '19560891'], [[['load', '显示子话题', '', '19560891'], []]]], 
            [['topic', '学科', '19618774'], [[['load', '显示子话题', '', '19618774'], []]]],
             [['topic', '「未归类」话题', '19776751'], [[['load', '显示子话题', '', '19776751'], []]]],
              [['topic', '「形而上」话题', '19778298'], [[['load', '显示子话题', '', '19778298'], []]]]]], 
              'r': 0}
              """
            if not response_login.json()["r"] == 0:
                return

            """解析子话题"""
            for tmp_topic in rep_msg["msg"][1]:
                if tmp_topic[0][1] == "加载更多":
                    last_topic = tmp_topic[0][2]
                    parent_topic = tmp_topic[0][3]
                    break
                topic_id = int(tmp_topic[0][2])
                self._child_topic_id.append(topic_id)
            else:
                continue_load = False # 没有"加载更多", 不再加载

    def _parse_top_answer_one_page(self, page):
        """解析一个精华回答页面，返回值:是否还有下一页"""

        self._debug_print(DebugLevel.verbose, "paser top answer of topic " + self._url + " " + self._name + " page" \
                        + str(page))

        page_url = self._url + r"/top-answers?page=" + str(page) #指定页码
        
        try:
            _, soup = ZhihuCommon.get(page_url) 
        except Exception as e:
            self._debug_print(DebugLevel.warning, "fail to get page " + page_url + "errinfo " + str(e))
            ZhihuCommon.get_and_save_page(page_url, "last_page_in_topic.html")
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
        self._debug_print(DebugLevel.verbose, "last page in topic " + page_url)   
        return False
        
    def _parse_top_answer(self):
        """解析精华回答"""
        go_next_page = True #是否解析下一页
        page = 1
        while go_next_page:
            go_next_page = self._parse_top_answer_one_page(page)
            page += 1
            if ZhihuCommon.debug_fast_crawler and page > 10:
                break #打开快速模式，仅搜索前十个页面

class ZhihuAnswer(object):
    
    def __init__(self, url):
        self._base_url = r"https://www.zhihu.com"
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
            _, soup = ZhihuCommon.get(self._url)     
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
            
            ans_content_tag = soup.find("div", class_="zm-editable-content clearfix")
            self._answer_len = 0;
            for ans_str in ans_content_tag.stripped_strings:
                self._answer_len += len(ans_str)

            self._debug_print(DebugLevel.verbose, "parse " + self._url  + " ok." + " " + self._question + "vote:" \
                + str(self._votecount) + " author:" + self._author_name + " answer_len: " + str(self._answer_len))
            
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
        tmp_dict["votecount"] = obj._votecount
        tmp_dict["answer_len"] = obj._answer_len
        
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
        tmp_dict["gender"] = obj._gender
        for key_str in ZhihuUser._extra_info_key:
            if key_str in obj._extra_info:
                tmp_dict[key_str] = obj._extra_info[key_str]
            else:
                tmp_dict[key_str] = ""
            
        return tmp_dict 
                
    def _parse_user_page(self):        
        try:      
            _, soup = ZhihuCommon.get(self._user_url)  
            self.soup = soup   
            #class_即是查找class，因为class是保留字，bs框架做了转化
            head_tag = soup.find("div", class_="zm-profile-header")
            name_tag = head_tag.find("span", class_="name")
            name = name_tag.contents[0]
            agree_tag = head_tag.find("span", class_="zm-profile-header-user-agree") 
            agree_cnt = agree_tag.contents[1].contents[0]
            thank_tag = head_tag.find("span", class_="zm-profile-header-user-thanks") 
            thank_cnt = thank_tag.contents[1].contents[0]
            gender_tag = head_tag.find("span", class_="item gender")
            #gender_tag.cont...nts[0]["class"]是一个list，list的每一个元素是字符串
            gender_str = gender_tag.contents[0]["class"][1]
            if gender_str.find("female") > 0:
                self._gender = "Female"
            elif gender_str.find("male") > 0:
                self._gender = "Male"
            else:
                self._gender = "Unknown gender"
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
            "thank: " + str(self._thank_cnt) + " " + self._gender + " "

        for key_str in self._extra_info_key:
            if key_str in self._extra_info:
                out_str += " " + key_str + ": " + self._extra_info[key_str]

        return out_str


class ZhihuCommon(object):
    """ZhihuCrawler, ZhihuTopic, ZhihuUser三个类的共用代码, 包含一些服务于debug的函数, 共用的网页获取函数, 等。"""
    
    root_topic = 19776749 # 19776749 根话题  19776751 未归类  19778298 形而上 
    unclassed_topic = 19776751
    my_header = {
        'Connection': 'Keep-Alive',
        'Accept': 'text/html, application/xhtml+xml, */*',
        'Accept-Language': 'zh-CN,zh;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Accept-Encoding': 'gzip,deflate,sdch',
        'Host': 'www.zhihu.com',
        'DNT': '1'
    }
    
    """运行参数"""
    debug_fast_crawler = False #快速模式是否打开，当此模式打开时，不会遍历所有同类的信息，用于调试。
    traversal_level_max = 3 #深度优化遍历最大层数限制
    user_json_file = "user.json"
    answer_json_file = "answer.json"
    topic_json_file = "topic.json"
    
    _last_get_page_fail = False #上一次调用get_page是失败的?
    _xsrf = None
    _session = None
    
    @staticmethod
    def set_xsrf(xsrf):
        ZhihuCommon._xsrf = xsrf
    
    @staticmethod
    def get_xsrf():
        return ZhihuCommon._xsrf
    
    @staticmethod
    def session_init():
        ZhihuCommon._session = requests.Session()
    
    @staticmethod
    def get_session():
        return ZhihuCommon._session
    
    @staticmethod
    def get(url):
        try_time = 0
        
        while try_time < 5:
            #上一次get页面失败，暂停10秒
            if ZhihuCommon._last_get_page_fail:
                time.sleep(10)
                
            try:
                try_time += 1
                response = ZhihuCommon.get_session().get(url, headers = ZhihuCommon.my_header, timeout = 30)
                #, cert = 'F:\Programs\Class-3-Public-Primary-Certification-Authority.pem')
                soup = BeautifulSoup(response.text)
                ZhihuCommon._last_get_page_fail = False
                return response.text, soup
            except Exception as e:
                print("fail to get " + url + " error info: " + str(e) + " try_time " + str(try_time))
                ZhihuCommon._last_get_page_fail = True
        else:
            raise #当前函数不知道应该怎么处理该错误，所以，最恰当的方式是继续往上抛，让顶层调用者去处理
    
    @staticmethod
    def post(url, post_dict):
        try_time = 0
        
        while try_time < 5:
            #上一次get页面失败，暂停10秒
            if ZhihuCommon._last_get_page_fail:
                time.sleep(10)
                
            try:
                try_time += 1
                response = ZhihuCommon.get_session().post(url, headers = ZhihuCommon.my_header, data = post_dict, timeout = 30)
                #, cert = 'F:\Programs\Class-3-Public-Primary-Certification-Authority.pem')
                ZhihuCommon._last_get_page_fail = False
                return response
            except Exception as e:
                print("fail to post " + url + " error info: " + str(e) + " try_time " + str(try_time))
                ZhihuCommon._last_get_page_fail = True
        else:
            raise #当前函数不知道应该怎么处理该错误，所以，最恰当的方式是继续往上抛，让顶层调用者去处理
        
    @staticmethod
    def get_and_save_page(url, path):
        try:
            response = ZhihuCommon.get_session().get(url, headers = ZhihuCommon.my_header,  verify = False)
            with codecs.open(path, 'w', response.encoding)  as fp:
                fp.write(response.text)
            return
        except Exception as e:
            print("fail to get " + url + " error info: " + str(e))
            return

class ZhihuAnalyse(object):
    """基于ZhihuCrawler的结果做分析"""
    def __init__(self):
        self._topics = deque()
        self._answers = deque()
        self._users = deque()
                        
    def _analyse_topic(self):        
        with open(ZhihuCommon.topic_json_file, "r") as fp:
            for line in fp.readlines():
                topic = json.loads(line)
                self._topics.append(topic)
    
    def _analyse_answer(self):
        with open(ZhihuCommon.answer_json_file, "r") as fp:
            for line in fp.readlines():
                answer = json.loads(line)
                self._answers.append(answer)
                
    def _analyse_user(self):
        with open(ZhihuCommon.user_json_file, "r") as fp:
            for line in fp.readlines():
                user = json.loads(line)
                self._users.append(user)
    
    def _analyse_gender(self):
        self.male_num = 0
        self.female_num = 0
        self.unknow_gender = 0
        for user in self._users:
            if user["gender"] == "Male":
                self.male_num += 1
            elif user["gender"] == "Female":
                self.female_num += 1
            else:
                self.unknow_gender += 1
        print("male: " + str(self.male_num) + " female: " + str(self.female_num) + 
            " unknow_gender: " + str(self.unknow_gender))
                
    
    def _analyse_votecount_ans_len(self):
        #答案投票数的分布，每个_votecount_distribution下标跨度为vote_dis_part
        #答案长度的分布，每个_ans_len_distribution下标跨度为ans_len_dis_part
        #下标个数为part_num
        vote_dis_part = 5000
        ans_len_dis_part = 100
        part_num = 500
        self._votecount_distribution = [0] * part_num
        self._ans_len_distribution = [0] * part_num
        self._max_votecount = 0
        self._max_ans_len = 0
        for ans in self._answers:
            idx = (int)(ans["votecount"] / vote_dis_part)
            if idx >= part_num:
                idx = part_num - 1
            self._votecount_distribution[idx] += 1
            if ans["votecount"] > self._max_votecount:
                self._max_votecount = ans["votecount"]
                
            idx = (int)(ans["answer_len"] / ans_len_dis_part)
            if idx >= part_num:
                idx = part_num - 1
            self._ans_len_distribution[idx] += 1
            if ans["answer_len"] > self._max_ans_len:
                self._max_ans_len = ans["answer_len"]
                
        max_idx = (int)(self._max_votecount / vote_dis_part + 1)
        if max_idx >= part_num:
            max_idx = part_num - 1
        print("Vote Count:")
        for idx in range(max_idx + 1):
            if idx == part_num - 1:
                print("    More than " + str(idx * vote_dis_part) + ": " 
                      + str(self._votecount_distribution[idx]))
            else:
                print("    " + str(idx * vote_dis_part) + "~" + str((idx + 1) * vote_dis_part) + ": " 
                      + str(self._votecount_distribution[idx]))
        
        max_idx = (int)(self._max_ans_len / ans_len_dis_part + 1)
        if max_idx >= part_num:
            max_idx = part_num - 1
        print("Answer Len:")
        for idx in range(max_idx + 1):
            if idx == part_num - 1:
                print("    More than " + str(idx * ans_len_dis_part) + ": " 
                      + str(self._ans_len_distribution[idx]))

            else:
                print("    " + str(idx * ans_len_dis_part) + "~" + str((idx + 1) * ans_len_dis_part) + ": " 
                      + str(self._ans_len_distribution[idx]))
        
    def do_analyse(self):
        self._analyse_topic()
        self._analyse_answer()
        self._analyse_user()
        self._analyse_gender()
        self._analyse_votecount_ans_len()
        pass
       
def main():
    z = ZhihuCrawler()
    z.init_xsrf()
    login_sucess = z.login()
    if not login_sucess:
        print("fail to login.")
        return
    z.do_crawler() 
    za = ZhihuAnalyse()
    za.do_analyse()
    
    print("ok\n")

if __name__ == "__main__":    
    main()
      
