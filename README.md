## 插件描述

使用代理 MidJourney 的discord频道[`midjourney-proxy`](https://github.com/novicezk/midjourney-proxy)的api在[`chatgpt-on-wechat`](https://github.com/zhayujie/chatgpt-on-wechat)进行请求绘图发送

本插件依赖于[`chatgpt-on-wechat`](https://github.com/zhayujie/chatgpt-on-wechat)而开发的插件
本插件基于[`midjourney-proxy`](https://github.com/novicezk/midjourney-proxy)，需要先部署该项目，起了该服务才能用接下来的mj_url进行配置，没有该服务无法使用

## 支持的平台
- [x] 可接入个人微信聊天使用[`chatgpt-on-wechat`](https://github.com/zhayujie/chatgpt-on-wechat)
- [x] 可接入企业微信应用使用[`企业微信应用号`](https://github.com/zhayujie/chatgpt-on-wechat/blob/master/channel/wechatcom/README.md)
- [x] 可接入微信公众号[`微信公众号`](https://github.com/zhayujie/chatgpt-on-wechat/blob/master/channel/wechatmp/README.md)，但由于个人主体的微信订阅号由于无法通过微信认证，无法主动发出消息，只能被动回复，存在回复时间限制(最多只有15秒的自动回复时间窗口)，所以可能无法及时发送图片，只能通过查询接口去拿，建议不使用个人公众号。

## 已对接现有功能
- [x] midjourney `imgine` 想象
- [x] midjourney `upscale` 放大
- [x] midjourney `variation` 变幻
- [x] midjourney `describe` 识图，使用方式：（1）私聊窗口（非群聊模式）发图直接生成；（2）发送describe_prefix配置的指令，然后发送一张图片进行识别（此方法不限群聊还是私聊方式）
- [x] midjourney `blend` 混图，使用方式：发送blend_prefix配置的指令，然后发送多张图片进行混合（此方法不限群聊还是私聊方式）
- [x] midjourney 垫图，使用方式：发送pad_prefix配置的指令+prompt描述，然后发送一张图片进行生成（此方法不限群聊还是私聊方式）
- [x] 绘图进度百分比查询
- [x] 发送/queue 任务队列查询
- [x] 解决webp图片无法发送问题
- [x] mj_tip可关闭多条消息发送（最终只发图片或者描述）
- [x] 可自定义添加修改各种功能prefix前缀
- [x] 聊天窗口管理员指令可修改管理员密码，配置mj_url,mj_api_secret，暂停启用mj服务

## 后续对接计划
- [ ] 聊天窗口插件可生成用户密钥(需管理员)，用户可通过设置用户密钥进行限制MJ服务使用对象，或配置mj_groups限制群聊使用
- [ ] 如有其他点子可提交[issues](https://github.com/mouxangithub/midjourney/issues)


## MJ指令说明

### 通用指令
- [x] $mj_help 说明文档
- [x] $mj_admin_password 口令 进行管理员认证(如未配置，默认管理员密码为123456)

### 管理员指令
- [x] $set_mj_admin_password 新口令 进行设置新密码
- [x] $set_mj_url mj代理地址 mj_api_secret请求参数 进行设置MJ服务器信息
- [x] $stop_mj 暂停MJ服务
- [x] $enable_mj 启用MJ服务
- [x] $clean_mj 清除MJ服务缓存

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
    "mj_tip": true, // 是否发送请求提示，让漫长的等待不会枯燥，如果嫌啰嗦可关闭，即：发送一些成功的内容
    "mj_admin_password": "", // MJ管理员密码
    "mj_admin_users": [], // 管理员用户，同godcmd
    "imagine_prefix": "[\"/i\", \"/mj\"]", // imagine画图触发前缀
    "fetch_prefix": "[\"/f\"]", // fetch任务查询触发前缀
    "up_prefix": "[\"/u\"]", // up图片放大和变换触发前缀
    "pad_prefix": "[\"/p\"]", // 垫图画图触发前缀
    "blend_prefix": "[\"/b\"]", // 混图画图触发前缀
    "describe_prefix": "[\"/d\"]", // 图生文触发前缀
    "queue_prefix": "[\"/q\"]",  // 查询正在执行中任务触发前缀
    "end_prefix": "[\"/e\"]"  // 结束存储打包发送任务（目前用于混图）触发前缀
}
## 第四步：#scanp扫描插件，提示发现MidJourney插件即为成功
#scanp
## 第五步：输入$mj_help有提示说明成功，输入/mj出图
```

### railway部署

```shell
## 第一步：前往Variables配置下方环境变量
mj_url= ""
mj_api_secret= ""
mj_tip=True
imagine_prefix="[\"/imagine\", \"/mj\", \"/img\"]"
fetch_prefix="[\"/fetch\", \"/ft\"]"
up_prefix="[\"/u\", \"/up\"]"
pad_prefix="[\"/p\", \"/pad\"]"
blend_prefix="[\"/b\", \"/blend\"]"
describe_prefix="[\"/d\", \"/describe\"]"
queue_prefix="[\"/q\"]"
end_prefix="[\"/e\"]"
## 第二步：重新部署redeploy
## 第三步：扫码登录进入聊天窗口，先认证管理员，如果是临时密码，请重启chatgpt-on-wechat前往logs查看，上方日志中有临时密码
#auth＋密码
## 第四步：认证成功后进行安装
#installp https://github.com/mouxangithub/midjourney.git
## 第五步：#scanp扫描插件，提示发现MidJourney插件即为成功
#scanp
## 第六步：输入$mj_help有提示说明成功，输入/mj出图
```

详细教程在[`插件文档`](https://github.com/zhayujie/chatgpt-on-wechat/tree/master/plugins#readme)和[`midjourney-proxy`](https://github.com/novicezk/midjourney-proxy)有说明

![Star History Chart](https://api.star-history.com/svg?repos=mouxangithub/midjourney&type=Date)
