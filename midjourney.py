# encoding:utf-8

import json
import os

import socket
import web
from requests_toolbelt import sessions

import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from channel.chat_message import ChatMessage
from common import const
from common.log import logger
from config import conf
from plugins import *


@plugins.register(name="midjourney", desire_priority=-1, desc="A simple plugin to summary messages", version="0.3", author="mouxan")
class midjourney(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        urls = ("/mj_notify", "plugins.midjourney.midjourney.Query")
        app = web.application(urls, globals(), autoreload=False)
        port = conf().get("mj_port", 80)
        web.httpserver.runsimple(app.wsgifunc(), ("0.0.0.0", port))
        self.http = sessions.BaseUrlSession(base_url=conf().get("mjProxyEndpoint", "http://mouxan.cn/mj"))
        logger.info("[MidJourney] inited")
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        logger.info("[本机IP] ip")
        

    def get_help_text(self, **kwargs):
        help_text = "欢迎使用MJ机器人\n"
        help_text += f"这是一个AI绘画工具，只要输入想到的文字，通过人工智能产出相对应的图。\n"
        help_text += f"------------------------------\n"
        help_text += f"🎨 AI绘图-使用说明：\n"
        help_text += f"输入: /imagine prompt\n"
        help_text += f"prompt 即你提的绘画需求\n"
        help_text += f"------------------------------\n"
        help_text += f"📕 prompt附加参数 \n"
        help_text += f"1.解释: 在prompt后携带的参数, 可以使你的绘画更别具一格\n"
        help_text += f"2.示例: /imagine prompt --ar 16:9\n"
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

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type not in [
            ContextType.TEXT,
            ContextType.IMAGE,
        ]:
            return
        
        content = e_context["context"].content
        isgroup = e_context["context"].isgroup
        msg: ChatMessage = e_context["context"]["msg"]
        reply = Reply()
        reply.type = ReplyType.TEXT
        trigger_prefix = conf().get("plugin_trigger_prefix", "$")

        if not content.startswith(f"{trigger_prefix}imagine") and not content.startswith(f"{trigger_prefix}up") :
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            return
        logger.debug("[MidJourney] 内容: %s" % content)
        response = None
        # 调用mj绘画
        if content.startswith(f"{trigger_prefix}imagine"):
            prompt = content[9:len(content)]
            response = self.on_request("/submit/imagine", {
                "state": msg.from_user_nickname,
                "prompt": prompt
            })
        else :
            prompt = content[4:len(content)]
            response = self.on_request("/submit/up", {
                "state": msg.from_user_nickname,
                "prompt": "up"
            })

        if not response:
            return
        if response.status_code == 22:
            reply.content = f"⏰ {response.json()['description']}"
        elif not response.status_code == 1:
            reply.content = f"❌ {response.json()['description']}"
        else:
            reply.content = f"提交成功，正在绘制中，请稍后..."
        e_context["reply"] = reply
        e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑

            
    
    def on_request(self, url, data):
        response = self.http.post(url, data={**data, "notifyHook": conf().get("notifyHook", "http://localhost/mj_notify")})
        logger.debug("[py_rq] response: %s" % response)
        if response.status_code == 200:
            return response.json()
        else:
            return None


class Query:
    def POST(self):
        params = web.input()
        logger.info("[wechat] receive params: {}".format(params))
        return "success"
