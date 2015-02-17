import urllib.request
import os
import sys

"""crawler study code """
 
url = "http://www.baidu.com"
data = urllib.request.urlopen(url).read()
web_str = data.decode("utf-8")

try:
    if not os.path.exists("tmp"):
        os.mkdir("tmp")
    local_file = open("tmp/local.htm", "w", encoding='utf-8')
    local_file.write(web_str)
    local_file.close()
except IOError as e:
    print("Could not open file:", e)

