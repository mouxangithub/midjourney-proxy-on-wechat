## 插件描述

使用代理 MidJourney 的discord频道[`midjourney-proxy`](https://github.com/novicezk/midjourney-proxy)的api在[`chatgpt-on-wechat`](https://github.com/zhayujie/chatgpt-on-wechat)进行请求绘图发送

MidJourney知道吧，懂的都懂，不懂的就自己百度哈

本插件依赖于[`chatgpt-on-wechat`](https://github.com/zhayujie/chatgpt-on-wechat)而开发的插件
本插件基于[`midjourney-proxy`](https://github.com/novicezk/midjourney-proxy)，需要先部署该项目，起了该服务才能用接下来的mj_url进行配置，没有该服务无法使用

## 已对接现有功能
- [x] midjourney `imgine` 想象
- [x] midjourney `upscale` 放大
- [x] midjourney `variation` 变幻
- [x] midjourney 垫图，算是半支持，需要输入imgine指令的时候带上图片URL（如果开启了翻译模式似乎就会把url剔除，稍后会出个直接发送/pad然后发图片进行垫图绘画）
- [x] 绘图进度百分比查询
- [x] 解决webp图片无法发送问题
- [x] /queue 任务队列查询
- [x] midjourney `describe` 识图，暂定方式：私聊窗口（非群聊模式）发图直接生成

## 后续对接计划
- [ ] midjourney 垫图，暂定方式：私聊窗口（非群聊模式）先发送/pad-img + 描述或自编指令，然后发图
- [ ] midjourney `blend` 混图，暂定方式：私聊窗口（非群聊模式）先发送/blend + 描述或自编指令，然后发图，最后发送/blend-end
- [ ] 聊天窗口插件可通过指令修改mj_url地址等配置
- [ ] 如有其他点子可提交[issues](https://github.com/mouxangithub/midjourney/issues)

## 使用说明
首先，先部署好[`midjourney-proxy`](https://github.com/novicezk/midjourney-proxy)，具体方法教程就点击[`midjourney-proxy`](https://github.com/novicezk/midjourney-proxy)前往查看文档部署，此处就不过多的粘贴复制了，敲代码敲累了，不复制了

Tips：部署midjourney-proxy后，下方mj_url不需要带/mj，只需域名/ip+端口；该插件读取不到docker-compose.yml的环境变量，所以不用去docker-compose.yml配置，具体原因回头再研究

### 本地运行和Docker部署

如果是本地或者docker部署的[`chatgpt-on-wechat`](https://github.com/zhayujie/chatgpt-on-wechat)，参考下方方法安装此插件：

插件安装：根据[`插件文档`](https://github.com/zhayujie/chatgpt-on-wechat/tree/master/plugins#readme)进行安装该插件

```shell
## 第一步：进入聊天窗口，先认证管理员，如果是临时密码，请重启chatgpt-on-wechat前往logs查看，上方日志中有临时密码
#auth＋密码
## 第二步：认证成功后进行安装
#installp https://github.com/mouxangithub/midjourney.git
## 第三步：前往插件目录/plugins/midjourney/config.json.template如果有config.json就直接改这个文件，加入下方配置
{
  "mj_url": "", // midjourney-proxy的服务地址
  "mj_api_secret": "", // midjourney-proxy的api请求头，如果midjourney-proxy没配置此处可以不配
  "imagine_prefix": "[\"/i\", \"/mj\", \"/imagine\", \"/img\"]", // imagine画图触发前缀
  "fetch_prefix": "[\"/f\", \"/fetch\"]", // fetch任务查询触发前缀
  "up_prefix": "[\"/u\", \"/up\"]", // up图片放大和变换触发前缀
  "pad_prefix": "[\"/p\", \"/pad\"]", // 垫图画图触发前缀
  "blend_prefix": "[\"/b\", \"/blend\"]", // 混图画图触发前缀
  "describe_prefix": "[\"/d\", \"/describe\"]" // 图生文触发前缀
}
## 第四步：#scanp扫描插件，提示发现MidJourney插件即为成功
#scanp
## 第五步：输入/mjhp有提示说明成功，输入/mj出图
```

### railway部署

```shell
## 第一步：前往Variables配置下方环境变量
mj_url= ""
mj_api_secret= ""
imagine_prefix="[\"/imagine\", \"/mj\", \"/img\"]"
fetch_prefix="[\"/fetch\", \"/ft\"]"
up_prefix="[\"/u\", \"/up\"]"
pad_prefix="[\"/p\", \"/pad\"]"
blend_prefix="[\"/b\", \"/blend\"]"
describe_prefix="[\"/d\", \"/describe\"]"
## 第二步：重新部署redeploy
## 第三步：扫码登录进入聊天窗口，先认证管理员，如果是临时密码，请重启chatgpt-on-wechat前往logs查看，上方日志中有临时密码
#auth＋密码
## 第四步：认证成功后进行安装
#installp https://github.com/mouxangithub/midjourney.git
## 第五步：#scanp扫描插件，提示发现MidJourney插件即为成功
#scanp
## 第六步：输入/mjhp有提示说明成功，输入/mj出图
```

详细教程在[`插件文档`](https://github.com/zhayujie/chatgpt-on-wechat/tree/master/plugins#readme)和[`midjourney-proxy`](https://github.com/novicezk/midjourney-proxy)有说明
