# encoding:utf-8
import time
import requests
import io
from PIL import Image
import re
import os
import json
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
import plugins
from plugins import *

def check_prefix(content, prefix_list):
    if not prefix_list:
        return False, None
    for prefix in prefix_list:
        if content.startswith(prefix):
            return True, content.replace(prefix, "").strip()
    return False, None

@plugins.register(
    name="MidJourney",
    namecn="MJ绘画",
    desc="一款AI绘画工具",
    version="1.0.19",
    author="mouxan",
    desire_priority=0
)
class MidJourney(Plugin):
    def __init__(self):
        super().__init__()

        gconf = {
            "mj_url": "",
            "mj_api_secret": "",
            "imagine_prefix": "[\"/i\", \"/mj\", \"/imagine\", \"/img\"]",
            "fetch_prefix": "[\"/f\", \"/fetch\"]",
            "up_prefix": "[\"/u\", \"/up\"]",
            "pad_prefix": "[\"/p\", \"/pad\"]",
            "blend_prefix": "[\"/b\", \"/blend\"]",
            "describe_prefix": "[\"/d\", \"/describe\"]"
        }

        # 读取和写入配置文件
        curdir = os.path.dirname(__file__)
        config_path = os.path.join(curdir, "config.json")
        config_template_path = os.path.join(curdir, "config.json.template")
        if os.environ.get("mj_url", None):
            logger.info("使用的是环境变量配置:mj_url={} mj_api_secret={} imagine_prefix={} fetch_prefix={}".format(self.mj_url, self.mj_api_secret, self.imagine_prefix, self.fetch_prefix))
            gconf = {
                "mj_url": os.environ.get("mj_url", ""),
                "mj_api_secret": os.environ.get("mj_api_secret", ""),
                "imagine_prefix": os.environ.get("imagine_prefix", "[\"/i\", \"/mj\", \"/imagine\", \"/img\"]"),
                "fetch_prefix": os.environ.get("fetch_prefix", "[\"/f\", \"/fetch\"]"),
                "up_prefix": os.environ.get("up_prefix", "[\"/u\", \"/up\"]"),
                "pad_prefix": os.environ.get("pad_prefix", "[\"/p\", \"/pad\"]"),
                "blend_prefix": os.environ.get("blend_prefix", "[\"/b\", \"/blend\"]"),
                "describe_prefix": os.environ.get("describe_prefix", "[\"/d\", \"/describe\"]")
            }
        elif os.path.exists(config_path):
            logger.info(f"使用的是插件目录下的config.json配置：{config_path}")
            with open(config_path, "r", encoding="utf-8") as f:
                z = json.load(f)
                gconf = {**gconf, **z}
        elif os.path.exists(config_template_path):
            logger.info(f"使用的是插件目录下的config.json.template配置：{config_template_path}")
            with open(config_template_path, "r", encoding="utf-8") as f:
                z = json.load(f)
                gconf = {**gconf, **z}
        else:
            logger.info("使用的是默认配置")

        if gconf["mj_url"] == "":
            logger.info("[MJ] 未设置[mj_url]，请前往环境变量进行配置或在该插件目录下的config.json进行配置。")

        # 重新写入配置文件
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(gconf, f, indent=4)
        
        self.mj_url = gconf["mj_url"]
        self.mj_api_secret = gconf["mj_api_secret"]

        if not gconf["imagine_prefix"]:
            self.imagine_prefix = ["/mj", "/imagine", "/img"]
        else:
            self.imagine_prefix = eval(gconf["imagine_prefix"])
        if not gconf["fetch_prefix"]:
            self.fetch_prefix = ["/ft", "/fetch"]
        else:
            self.fetch_prefix = eval(gconf["fetch_prefix"])
        if not gconf["up_prefix"]:
            self.up_prefix = ["/u", "/up"]
        else:
            self.up_prefix = eval(gconf["up_prefix"])
        if not gconf["pad_prefix"]:
            self.pad_prefix = ["/p", "/pad"]
        else:
            self.pad_prefix = eval(gconf["pad_prefix"])
        if not gconf["blend_prefix"]:
            self.blend_prefix = ["/b", "/blend"]
        else:
            self.blend_prefix = eval(gconf["blend_prefix"])
        if not gconf["describe_prefix"]:
            self.describe_prefix = ["/d", "/describe"]
        else:
            self.describe_prefix = eval(gconf["describe_prefix"])
        
        self.mj = _mjApi(self.mj_url, self.mj_api_secret, self.imagine_prefix, self.fetch_prefix, self.up_prefix, self.pad_prefix, self.blend_prefix, self.describe_prefix)

        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        logger.info("[MJ] inited. mj_url={} mj_api_secret={} imagine_prefix={} fetch_prefix={}".format(self.mj_url, self.mj_api_secret, self.imagine_prefix, self.fetch_prefix))

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type not in [
            ContextType.TEXT,
        ]:
            return

        channel = e_context['channel']
        context = e_context['context']
        content = context.content

        # 判断是否是指令
        iprefix, iq = check_prefix(content, self.imagine_prefix)
        fprefix, fq = check_prefix(content, self.fetch_prefix)
        uprefix, uq = check_prefix(content, self.up_prefix)
        pprefix, pq = check_prefix(content, self.pad_prefix)
        bprefix, bq = check_prefix(content, self.blend_prefix)
        dprefix, dq = check_prefix(content, self.describe_prefix)

        reply = None
        if content == "/mjhp" or content == "/mjhelp" or content == "/mj-help":
            self.env_detection(e_context)
            reply = Reply(ReplyType.INFO, self.mj.help_text())
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            return
        elif iprefix == True:
            self.env_detection(e_context)
            logger.debug("[MJ] /imagine iprefix={} iq={}".format(iprefix,iq))
            status, msg, id = self.mj.imagine(iq)
            if status:
                self.sendMsg(channel, context, ReplyType.TEXT, msg)
                status2, msgs, imageUrl = self.mj.get_f_img(id)
                if status2:
                    self.sendMsg(channel, context, ReplyType.TEXT, msgs)
                    reply = Reply(ReplyType.IMAGE_URL, imageUrl)
                else:
                    reply = Reply(ReplyType.ERROR, msgs)
            else:
                reply = Reply(ReplyType.ERROR, msg)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return
        elif uprefix == True:
            self.env_detection(e_context)
            logger.debug("[MJ] /up uprefix={} uq={}".format(iprefix,iq))
            status, msg, id = self.mj.simpleChange(uq)
            if status:
                self.sendMsg(channel, context, ReplyType.TEXT, msg)
                status2, msgs, imageUrl = self.mj.get_f_img(id)
                if status2:
                    self.sendMsg(channel, context, ReplyType.TEXT, msgs)
                    reply = Reply(ReplyType.IMAGE_URL, imageUrl)
                else:
                    reply = Reply(ReplyType.ERROR, msgs)
            else:
                reply = Reply(ReplyType.ERROR, msg)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return
        elif fprefix == True:
            self.env_detection(e_context)
            logger.debug("[MJ] /fetch fprefix={} fq={}".format(fprefix,fq))
            status, msg, imageUrl = self.mj.fetch(fq)
            if status:
                if imageUrl:
                    self.sendMsg(channel, context, ReplyType.TEXT, msg)
                    reply = Reply(ReplyType.IMAGE_URL, imageUrl)
                else:
                    reply = Reply(ReplyType.TEXT, msg)
            else:
                reply = Reply(ReplyType.ERROR, msg)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return
        elif dprefix == True and not context["isgroup"]:
            self.env_detection(e_context)
            logger.debug("[MJ] /describe fprefix={} fq={}".format(fprefix,fq))

    def get_help_text(self, isadmin=False, isgroup=False, verbose=False,**kwargs):
        if kwargs.get("verbose") != True:
            return "这是一个AI绘画工具，只要输入想到的文字，通过人工智能产出相对应的图。"
        else:
            return self.mj.help_text()
    
    def env_detection(self, e_context: EventContext):
        if not self.mj_url:
            reply = Reply(ReplyType.ERROR, "未设置[mj_url]，请前往环境变量进行配置或在该插件目录下的config.json进行配置。")
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return
    
    def sendMsg(self, channel, context, types, msg):
        return channel._send_reply(context, channel._decorate_reply(context, Reply(types, msg)))



class _mjApi:
    def __init__(self, mj_url, mj_api_secret, imagine_prefix, fetch_prefix, up_prefix, pad_prefix, blend_prefix, describe_prefix):
        self.baseUrl = mj_url
        self.headers = {
            "Content-Type": "application/json",
        }
        if mj_api_secret:
            self.headers["mj-api-secret"] = mj_api_secret
        if imagine_prefix:
            self.imagine_prefix = imagine_prefix
        if fetch_prefix:
            self.fetch_prefix = fetch_prefix
        if up_prefix:
            self.up_prefix = up_prefix
        if pad_prefix:
            self.pad_prefix = pad_prefix
        if blend_prefix:
            self.blend_prefix = blend_prefix
        if describe_prefix:
            self.describe_prefix = describe_prefix
    
    def imagine(self, text):
        try:
            url = self.baseUrl + "/mj/submit/imagine"
            data = {"prompt": text}
            res = requests.post(url, json=data, headers=self.headers)
            code = res.json()["code"]
            if code == 1:
                msg = "✅ 您的任务已提交\n"
                msg += f"🚀 正在快速处理中，请稍后\n"
                msg += f"📨 ID: {res.json()['result']}\n"
                msg += f"🪄 进度\n"
                msg += f"✏  使用[{self.fetch_prefix[0]} + 任务ID操作]\n"
                msg += f"{self.fetch_prefix[0]} {res.json()['result']}"
                return True, msg, res.json()["result"]
            else:
                return False, res.json()["failReason"]
        except Exception as e:
            return False, "图片生成失败"
    
    def simpleChange(self, content):
        try:
            url = self.baseUrl + "/mj/submit/simple-change"
            data = {"content": content}
            res = requests.post(url, json=data, headers=self.headers)
            code = res.json()["code"]
            if code == 1:
                msg = "✅ 您的任务已提交\n"
                msg += f"🚀 正在快速处理中，请稍后\n"
                msg += f"📨 ID: {res.json()['result']}\n"
                msg += f"🪄 进度\n"
                msg += f"✏  使用[{self.fetch_prefix[0]} + 任务ID操作]\n"
                msg += f"{self.fetch_prefix[0]} {res.json()['result']}"
                return True, msg, res.json()["result"]
            else:
                return False, res.json()["failReason"]
        except Exception as e:
            return False, "图片生成失败"
    
    def fetch(self, id):
        try:
            url = self.baseUrl + f"/mj/task/{id}/fetch"
            res = requests.get(url, headers=self.headers)
            status = res.json()['status']
            startTime = ""
            finishTime = ""
            if res.json()['startTime']:
                startTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(res.json()['startTime']/1000))
            if res.json()['finishTime']:
                finishTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(res.json()['finishTime']/1000))
            msg = "✅ 查询成功\n"
            msg += f"ID: {res.json()['id']}\n"
            msg += f"内容：{res.json()['prompt']}\n"
            msg += f"状态：{self.status(status)}\n"
            msg += f"进度：{res.json()['progress']}\n"
            if startTime:
                msg += f"开始时间：{startTime}\n"
            if finishTime:
                msg += f"完成时间：{finishTime}\n"
            if res.json()['imageUrl']:
                return True, msg, res.json()['imageUrl']
            return True, msg, None
        except Exception as e:
            logger.exception(e)
            return False, f"查询失败: {e}", None
    
    def describe(self, base64):
        try:
            url = self.baseUrl + "/mj/submit/describe"
            data = {"base64": base64}
            res = requests.post(url, json=data, headers=self.headers)
            code = res.json()["code"]
            if code == 1:
                msg = "✅ 您的任务已提交\n"
                msg += f"🚀 正在快速处理中，请稍后\n"
                msg += f"📨 ID: {res.json()['result']}\n"
                msg += f"🪄 进度\n"
                msg += f"✏  使用[{self.fetch_prefix[0]} + 任务ID操作]\n"
                msg += f"{self.fetch_prefix[0]} {res.json()['result']}"
                return True, msg, res.json()["result"]
            else:
                return False, res.json()["description"]
        except Exception as e:
            return False, "图片获取失败"
    
    def status(self, status):
        msg = ""
        if status == "SUCCESS":
            msg = "已成功"
        elif status == "FAILURE":
            msg = "失败"
        elif status == "SUBMITTED":
            msg = "已提交"
        elif status == "IN_PROGRESS":
            msg = "处理中"
        else:
            msg = "未知"
        return msg
    
    def get_f_img(self, id):
        try:
          url = self.baseUrl + f"/mj/task/{id}/fetch"
          status = ""
          rj = ""
          while status != "SUCCESS":
              time.sleep(3)
              res = requests.get(url, headers=self.headers)
              rj = res.json()
              status = rj["status"]
          action = rj["action"]
          msg = ""
          if action == "IMAGINE":
              msg = f"🎨 绘图成功\n"
              msg += f"📨 ID: {id}\n"
              msg += f"✨ 内容: {rj['prompt']}\n"
              msg += f"🪄 放大 U1～U4，变换 V1～V4\n"
              msg += f"✏ 使用[{self.up_prefix[0]} 任务ID 操作]\n"
              msg += f"{self.up_prefix[0]} {id} U1"
          elif action == "UPSCALE":
              msg = "🎨 放大成功\n"
              msg += f"✨ {rj['description']}\n"
          return True, msg, rj["imageUrl"]
        except Exception as e:
            return False, "绘图失败"
    
    def help_text(self):
        help_text = "欢迎使用MJ机器人\n"
        help_text += f"这是一个AI绘画工具，只要输入想到的文字，通过人工智能产出相对应的图。\n"
        help_text += f"------------------------------\n"
        help_text += f"🎨 AI绘图-使用说明：\n"
        help_text += f"输入: /mj prompt\n"
        help_text += f"prompt 即你提的绘画需求\n"
        help_text += f"------------------------------\n"
        help_text += f"📕 prompt附加参数 \n"
        help_text += f"1.解释: 在prompt后携带的参数, 可以使你的绘画更别具一格\n"
        help_text += f"2.示例: /mj prompt --ar 16:9\n"
        help_text += f"3.使用: 需要使用--key value, key和value空格隔开, 多个附加参数空格隔开\n"
        help_text += f"------------------------------\n"
        help_text += f"📗 附加参数列表\n"
        help_text += f"1. --v 版本 1,2,3,4,5 默认5, 不可与niji同用\n"
        help_text += f"2. --niji 卡通版本 空或5 默认空, 不可与v同用\n"
        help_text += f"3. --ar 横纵比 n:n 默认1:1\n"
        help_text += f"4. --q 清晰度 .25 .5 1 2 分别代表: 一般,清晰,高清,超高清,默认1\n"
        help_text += f"5. --style 风格 (4a,4b,4c)v4可用 (expressive,cute)niji5可用\n"
        help_text += f"6. --s 风格化 1-1000 (625-60000)v3"
        return help_text