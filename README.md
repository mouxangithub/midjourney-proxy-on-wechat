## 插件描述

使用代理 MidJourney 的discord频道[`midjourney-proxy`](https://github.com/novicezk/midjourney-proxy)的api在[`chatgpt-on-wechat`](https://github.com/zhayujie/chatgpt-on-wechat)进行请求绘图发送

MidJourney知道吧，懂的都懂，不懂的就自己百度哈

本插件依赖于[`chatgpt-on-wechat`](https://github.com/zhayujie/chatgpt-on-wechat)而开发的插件
本插件基于[`midjourney-proxy`](https://github.com/novicezk/midjourney-proxy)，需要先部署该项目，起了该服务才能用接下来的mj_url进行配置，没有该服务无法使用

## 已对接现有功能
- [x] midjourney `imgine` 想象
- [x] midjourney `upscale` 放大
- [x] midjourney `variation` 变幻
- [x] midjourney 垫图，算是半支持，需要输入imgine指令的时候带上图片URL
- [x] 绘图进度百分比查询

## 后续对接计划
- [ ] midjourney `blend` 混图
- [ ] midjourney `describe` 识图
- [ ] 解决webp图片无法发送问题

## 使用说明
首先，先部署好[`midjourney-proxy`](https://github.com/novicezk/midjourney-proxy)，具体方法教程就点击[`midjourney-proxy`](https://github.com/novicezk/midjourney-proxy)前往查看文档部署，此处就不过多的粘贴复制了，敲代码敲累了，不复制了

然后，如果是railway部署的，则在环境变量中加上
```shell
mj_url= "" // mj代理部署的地址，必填，没有肯定是出不了图啦
mj_api_secret= "" // mj代理如若配置了mj.api-secret则此处同步，没有就不管
imagine_prefix="[\"/imagine\", \"/mj\", \"/img\"]" // 此处是触发imagine画图指令的前缀关键字
fetch_prefix="[\"/fetch\", \"/ft\"]" // 此处是触发fetch查询任务关键字
```
如果是本地的话可以在该插件的目录下的json文件(/plugins/godcm/config.json)进行修改
```shell
## /plugins/godcm/config.json
{
    mj_url= "" // mj代理部署的地址，必填，没有肯定是出不了图啦
    mj_api_secret= "" // mj代理如若配置了mj.api-secret则此处同步，没有就不管
    imagine_prefix="[\"/imagine\", \"/mj\", \"/img\"]" // 此处是触发imagine画图指令的前缀关键字
    fetch_prefix="[\"/fetch\", \"/ft\"]" // 此处是触发fetch查询任务关键字
}
```

最后，根据[`插件安装方法`]([https://github.com/novicezk/midjourney-proxy](https://github.com/zhayujie/chatgpt-on-wechat/tree/master/plugins#%E6%8F%92%E4%BB%B6%E5%AE%89%E8%A3%85%E6%96%B9%E6%B3%95)https://github.com/zhayujie/chatgpt-on-wechat/tree/master/plugins#%E6%8F%92%E4%BB%B6%E5%AE%89%E8%A3%85%E6%96%B9%E6%B3%95)进行安装

进入聊天窗口，首先需要先开启管理员权限才能进行安装（如果本地未设密码就前往logs查看，有一个"因未设置口令，本次的临时口令为:xxxx"四位数即为你的临时密码，本地的话就可以直接在/plugins/godcm/config.json进行设置固定密码）
然后在聊天窗口输入
```shell
#auth＋密码
```
然后输入下方指令进行安装
```shell
#installp https://github.com/mouxangithub/midjourney.git
```
然后输入/mjhp看看有没有发出说明，或者直接/mj + 描述出图

详细教程在[`插件安装方法`]([https://github.com/novicezk/midjourney-proxy](https://github.com/zhayujie/chatgpt-on-wechat/tree/master/plugins#%E6%8F%92%E4%BB%B6%E5%AE%89%E8%A3%85%E6%96%B9%E6%B3%95)https://github.com/zhayujie/chatgpt-on-wechat/tree/master/plugins#%E6%8F%92%E4%BB%B6%E5%AE%89%E8%A3%85%E6%96%B9%E6%B3%95)有说明
