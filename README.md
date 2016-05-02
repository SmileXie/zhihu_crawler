小趴趴--知乎版
================================
对知乎精华回答的爬虫收集与分析。

* 20160502：近日知乎登录添加了验证码机制，当前的代码已无法实现自动登录知乎

##算法简述
* 收集范围：知乎各话题下的精华回答。
* 爬虫算法：
  * 以[根话题的话题树](https://www.zhihu.com/topic/19776749/organize/entire)为启始，按广度优先遍历各子话题，深度为3。
![目录树](https://raw.githubusercontent.com/SmileXie/zhihu_crawler/master/images/topic_tree.png)
  * 各话题下的精华回答，按页遍历，例如从 https://www.zhihu.com/topic/19776749/top-answers?page=1
遍历到
https://www.zhihu.com/topic/19776749/top-answers?page=50
解析各精华回答
* 解析精华回答的各项属性，包括：
  * 精华回答的点赞数，答案长度；
  * 答题用户的id，获得的点赞数，地区，性别，学历，学校，专业等信息

##统计结果
* 统计结果请见：[http://www.jianshu.com/p/6d53b34165d2](http://www.jianshu.com/p/6d53b34165d2)
