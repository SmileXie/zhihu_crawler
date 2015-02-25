"""
crawler study code 

Author: smilexie1113@gmail.com

"""

import urllib.request
import os
import re
from collections import deque
from filecmp import cmp

ERROR_RETURN = "ERROR:"
def retrun_is_error(return_str):
    return return_str[0 : len(ERROR_RETURN)] == ERROR_RETURN
        

def python_cnt(str):
    return str.count("python")


def get_one_page(url):
    try:
        urlfd =  urllib.request.urlopen(url, timeout = 2)
    except Exception as ex:
        return ERROR_RETURN + ("URL " + "\"" + url + "\"" + " open failed. " + str(ex))
        
    if "html" not in urlfd.getheader("Content-Type"):
        return ERROR_RETURN + ("URL " + "\"" + url + "\"" + "is not html page.")
    
    try:
        html_str = urlfd.read().decode("utf-8")
    except:
        return ERROR_RETURN + ("Fail to decode URL " + "\"" + url + "\"" + ".")
    
    return html_str


if __name__ == "__main__":
    start_url = "http://news.dbanotes.net/"
    
    to_be_visited = deque()
    visited = set()
    
    cnt = 0
    py_str_cnt = 0
    to_be_visited.append(start_url)
    
    while to_be_visited:
        url = to_be_visited.popleft()        
        
        print(str(cnt) + "page(s) has been grabbed." + "URL " + "\"" + url + "\"" + " is being grabbed.")
        
        html_str = get_one_page(url)
        if retrun_is_error(html_str):
            print(html_str)
            continue            
        
        cnt += 1
        visited |= {url}
        
        py_cnt_tmp = python_cnt(html_str)
        if py_cnt_tmp != 0:
            py_str_cnt += py_cnt_tmp
            print("Find %d \"python\" , total count %d" % (py_cnt_tmp, py_str_cnt))

        #todo: parse the html_str
        
        link_pattern = re.compile('href=\"(.+?)\"') #links' regular expression       
        for tmp_url in link_pattern.findall(html_str):
            if "http" in tmp_url and tmp_url not in visited:
                to_be_visited.append(tmp_url)
        

