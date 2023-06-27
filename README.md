## 插件描述

MidJourney知道吧，懂的都懂，不懂的就自己百度哈

本插件基于[`MidJourney的discord频道代理`](https://github.com/novicezk/midjourney-proxy)

## 使用说明

首先，先部署好[`MidJourney的discord频道代理`](https://github.com/novicezk/midjourney-proxy)，具体方法教程就点击[`MidJourney的discord频道代理`](https://github.com/novicezk/midjourney-proxy)前往查看文档部署，此处就不过多的粘贴复制了，敲代码敲累了，不复制了

然后，如果是railway部署的，则在环境变量中加上
```shell
mj_url= "" // mj代理部署的地址，必填，没有肯定是出不了图啦
mj_api_secret= "" // mj代理如若配置了mj.api-secret则此处同步，没有就不管
imagine_prefix=["/imagine", "/mj", "/img"] // 此处是触发imagine画图指令的前缀关键字
fetch_prefix=["/fetch", "/ft"] // 此处是触发fetch查询任务关键字
```

最后，根据[`插件安装方法`]([https://github.com/novicezk/midjourney-proxy](https://github.com/zhayujie/chatgpt-on-wechat/tree/master/plugins#%E6%8F%92%E4%BB%B6%E5%AE%89%E8%A3%85%E6%96%B9%E6%B3%95)https://github.com/zhayujie/chatgpt-on-wechat/tree/master/plugins#%E6%8F%92%E4%BB%B6%E5%AE%89%E8%A3%85%E6%96%B9%E6%B3%95)进行安装
需要先开启管理员权限输入#auth＋密码，教程在[`插件安装方法`]([https://github.com/novicezk/midjourney-proxy](https://github.com/zhayujie/chatgpt-on-wechat/tree/master/plugins#%E6%8F%92%E4%BB%B6%E5%AE%89%E8%A3%85%E6%96%B9%E6%B3%95)https://github.com/zhayujie/chatgpt-on-wechat/tree/master/plugins#%E6%8F%92%E4%BB%B6%E5%AE%89%E8%A3%85%E6%96%B9%E6%B3%95)有说明，
然后输入#installp https://github.com/mouxangithub/midjourney.git进行安装
然后输入/mjhp看看有没有发出说明，或者直接/mj + 描述出图
