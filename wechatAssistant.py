# encoding:utf-8
from concurrent.futures import ThreadPoolExecutor
import itchat
from itchat.content import *
import asyncio,logging,json
from Tool.llm import ask
from Tool.browse import google,sumPage

@itchat.msg_register([TEXT, SHARING])
def handler_single_msg(msg):
    weChat().handle(msg)
    return None

@itchat.msg_register([TEXT, SHARING], isGroupChat=True)
def handler_group_msg(msg):
    weChat().handle_group(msg)
    return None

class weChat():
    def __init__(self):
        pass
    def startup(self):
        # login by scan QRCode
        itchat.auto_login(hotReload=True)
        # start message listener
        itchat.run()

    def handle(self, msg):
        thread_pool.submit(self._do_send, msg['Text'],msg['FromUserName'])

    def handle_group(self, msg):
        if not msg['IsAt']:
            return
        query = msg['Content'][len(msg['ActualNickName']) + 1:]
        if query is not None:
            thread_pool.submit(self._do_send_group, query, msg)

    def send(self, msg, receiver):
        itchat.send(msg, toUserName=receiver)

    def _do_send(self, query,reply_user_id):
        if query == '':
            return
        try:
            reply_text = self.reply(query)
            if reply_text is not None:
                self.send('GPT:' + reply_text,reply_user_id)
        except Exception as e:
            log.exception(e)

    def _do_send_group(self, query, msg):
        if not query:
            return
        group_id = msg['User']['UserName']
        reply_text = self.reply(query)
        if reply_text is not None:
            self.send('@' + msg['ActualNickName'] + ' ' + reply_text.strip(), group_id)

    def reply(self,queryText):
        reply_text=''
        if queryText.startswith('！') or queryText.startswith('! '):
            serp = google(queryText[2:]).split('\n')
            for x in serp[:10]:
                if x.startswith('https://'):
                    reply_text += '\n\n%s\n'%x+sumPage(x,model='openai/gpt-3.5-turbo-1106',lang='中文')
            return reply_text

if __name__=='__main__':
    log = logging.getLogger('itchat')
    log.setLevel(logging.DEBUG)
    thread_pool = ThreadPoolExecutor(max_workers=8)
    wechat = weChat()
    wechat.startup()
