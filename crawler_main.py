import urllib.request
import os
import sys

"""crawler study code """

if __name__ == "__main__":
    search_info = {}
    search_info["word"] = "2015羊年"
    search_str = urllib.parse.urlencode(search_info)
    url_pre = "http://www.baidu.com/s?"
    url_full = url_pre + search_str
    data = urllib.request.urlopen(url_full).read()
    web_str = data.decode("utf-8")
    
    try:
        if not os.path.exists("tmp"):
            os.mkdir("tmp")
        with open("tmp/local.htm", "w", encoding='utf-8') as local_file:
            local_file.write(web_str)
            
    except IOError as e:
        print("Could not open file:", e)

