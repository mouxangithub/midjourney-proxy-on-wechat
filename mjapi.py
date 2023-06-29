import time
import requests
from common.log import logger

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
                return False, res.json()["failReason"], None
        except Exception as e:
            logger.exception(e)
            return False, "图片生成失败", None
    
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
                return False, res.json()["failReason"], None
        except Exception as e:
            logger.exception(e)
            return False, "图片生成失败", None
    
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
            msg += f"内容(英文)：{res.json()['promptEn']}\n"
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
                return False, res.json()["description"], None
        except Exception as e:
            logger.exception(e)
            return False, "图片获取失败", None
    
    def get_f_img(self, id):
        try:
          url = self.baseUrl + f"/mj/task/{id}/fetch"
          status = ""
          rj = ""
          while status != "SUCCESS" or status != "FAILURE":
              time.sleep(3)
              res = requests.get(url, headers=self.headers)
              rj = res.json()
              status = rj["status"]
          action = rj["action"]
          msg = ""
          startTime = ""
          finishTime = ""
          if status != "SUCCESS":
              if res.json()['startTime']:
                  startTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(res.json()['startTime']/1000))
              if res.json()['finishTime']:
                  finishTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(res.json()['finishTime']/1000))
              if action == "IMAGINE":
                  msg = f"🎨 绘图成功\n"
                  msg += f"📨 ID: {id}\n"
                  msg += f"✨ 内容: {rj['prompt']}\n"
                  msg += f"✨ 内容(英文): {rj['promptEn']}\n"
                  msg += f"🪄 放大 U1～U4，变换 V1～V4\n"
                  msg += f"✏ 使用[{self.up_prefix[0]} 任务ID 操作]\n"
                  msg += f"{self.up_prefix[0]} {id} U1"
              elif action == "UPSCALE":
                  msg = "🎨 放大成功\n"
                  msg += f"✨ {rj['description']}\n"
              elif action == "VARIATION":
                  msg = "🎨 变换成功\n"
                  msg += f"✨ {rj['description']}\n"
              elif action == "DESCRIBE":
                  msg = "🎨 转述成功\n"
                  msg += f"✨ 内容: {rj['prompt']}\n"
                  msg += f"✨ 内容(英文): {rj['promptEn']}\n"
                  msg += f"✨ 地址: {rj['imageUrl']}\n"
              if rj["imageUrl"]:
                  return True, msg, rj["imageUrl"]
              return True, msg, None
          else:
            return False, f"请求失败：{res.json()['failReason']}", None
        except Exception as e:
            logger.exception(e)
            return False, "请求失败", None
    
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