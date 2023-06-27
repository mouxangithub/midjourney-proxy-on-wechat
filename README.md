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
