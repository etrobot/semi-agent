import os
import re
import time as t
from datetime import datetime,timedelta
import pandas as pd
import requests
from bs4 import BeautifulSoup
from Tool.llm import summarize, make_list, ask
from duckduckgo_search import DDGS
from config import SEARCHSITE,MODEL
from feedparser import parse
import smtplib
from email.mime.text import MIMEText
from email.header import Header

def sendEmail(message:str,receiver:str=os.environ['MAILTO'],subject:str=''):
    if len(message)==0:
        return
    message=message.replace('<td','<td style="border:1px solid grey;"').replace('<table','<table style="border-collapse:collapse;"')
    subject=datetime.now().strftime('%Y年%m月%d日')+subject
    sender = 'acephi@163.com' #发送的邮箱
    receiver = receiver.split(';')  #要接受的邮箱（注:测试中发送其他邮箱会提示错误）
    smtpserver = 'smtp.163.com'
    username = 'acephi' #你的邮箱账号
    password = os.environ['MAIL'] #你的邮箱密码
    msg = MIMEText(message,'html','utf-8') #中文需参数‘utf-8'，单字节字符不需要
    msg['Subject'] = Header(subject, 'utf-8') #邮件主题
    msg['from'] = sender    #自己的邮件地址
    smtp = smtplib.SMTP()
    try :
        smtp.connect(smtpserver) # 链接
        smtp.login(username, password) # 登陆
        smtp.sendmail(sender, receiver, msg.as_string()) #发送
        print('邮件发送成功')
    except smtplib.SMTPException:
        print('邮件发送失败')
    smtp.quit() # 结束


def sumPage(url: str,model=MODEL,lang='English',raw:bool=False,nitter=os.environ['NITTER']) -> str:
    print('Sum:',url)
    headers = {
        'accept-language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6,ja;q=0.5',
    }
    session = requests.Session()
    session.headers = headers
    try:
        if url.startswith('https://twitter.com') or url.startswith('https://x.com'):
            url = url.replace('https://twitter.com', nitter).replace('https://x.com', nitter)
            response = session.get(url)
        else:
            response = session.get("http://webcache.googleusercontent.com/search?q=cache:"+url[len('https://'):])
        if '<p><b>404.</b> <ins>That’s an error.</ins>' in response.text:
            headers['User-Agent']="Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Mobile Safari/537.36"
            session.headers = headers
            response = session.get(url)
        if not raw:
            soup = BeautifulSoup(response.text, 'html.parser')
            elements = [
                element.text for element in soup.find_all(["title", "h1", "h2", "h3", "li", "p","a"])
                if len(element.text) > 5
            ]
            txt = ' '.join(elements)
            print(len(txt),'/',len(response.text),url)
            return summarize(txt,model,lang)
        return response.text

    except Exception as e:
        print(e)
        return ''

def google(prompt:str,modle=MODEL)->str:
    SEARCH_ENGINE_ID = os.environ['SEARCH_ENGINE']
    API_KEY = os.environ['GOOGLE_API_KEY']
    url = f"https://www.googleapis.com/customsearch/v1?key={API_KEY}&cx={SEARCH_ENGINE_ID}&q={prompt}&start=1"
    data = requests.get(url).json()["items"]
    return  '\n'.join(f'{x["title"]}\n{x["link"]}' for x in data)

def search(prompt:str,model=MODEL)->str:
    details=[prompt]
    print(details)
    if len(prompt)>50:
        prompt = f'I want to search this info:『{prompt}』,plz make several groups of keywords'
        details = make_list(prompt,subList=True)
    final=[]
    def ddg(searchsite=SEARCHSITE):
        if 'SEARCHSITE' in os.environ.keys():
            searchsite=os.environ['SEARCHSITE']
        serp = ddgs.text(searchsite + ' ' + str(words), max_results=3)
        links = [r['href'] for r in serp]
        print('search result:', links)
        pageSum = '\n'.join(sumPage(link) for link in links)
        if len(pageSum) < 2560:
            sumSum = pageSum
        else:
            sumSum = summarize(pageSum,model)
        print('sumSum:', sumSum)
        final.append(sumSum)
        t.sleep(30)  # ddg limit

    for words in details[:3]:
        print('search:', words)
        if 'SOCKSPROXY' in os.environ.keys():
            with DDGS(proxies = os.environ['SOCKSPROXY']) as ddgs:
                ddg()
        else:
            with DDGS() as ddgs:
                ddg()

    return '\n'.join(make_list('\n'.join(final),model))

def wechatPost(url:str):
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    query = soup.get_text(separator="\n")
    for s in soup(['script', 'style']):
        s.decompose()
    soup=soup.find(id='js_content')
    query1 = [x.get_text(separator='\n') for x in soup.find_all('section')]
    query2 = [x.get_text(separator='\n') for x in soup.find_all('p')]
    if len(''.join(query2)) > len(''.join(query1)):
        query1 = query2
    if len('\n'.join(query1)) == 0:
        queryText = re.sub(r'\\x[0-9a-fA-F]{2}', '',
                           soup.find('meta', {'name': 'description'}).attrs['content'])
    else:
        query1 = '\n'.join(query1).split('\n')
        query = list(set(query1))
        query.sort(key=query1.index)
        queryText = '\n'.join(query)
    print(query[0],len(queryText))
    img_tags = soup.find_all('img')
    image_urls = '\n'.join(img.get('data-src','') for img in img_tags)+'\n'
    return image_urls,queryText

def get_rss_df(rss_url:str):
    feed = parse(rss_url)
    df = pd.json_normalize(feed.entries)
    return df

def sumTweets(users:str='elonmusk',info:str='人工智能',lang:str='中文',ingores:str="webinar",length:int=4000,nitter:str=os.environ['NITTER'],minutes:int=720,mail:bool=True,model=MODEL):
      result=''
      for user in users.split(';'):
        rss_url=f'https://{nitter}/{user}/rss'
        df=get_rss_df(rss_url)
        df['timestamp'] = df['published'].apply(lambda x: pd.Timestamp(x).timestamp())
        if not 'i/lists' in user:
            df = df.reindex(index=df.index[::-1])
        compareTime = datetime.utcnow() - timedelta(minutes=minutes)
        compareTime = pd.Timestamp(compareTime).timestamp()
        df = df[df['timestamp'] > compareTime]
        if len(df)==0:
            continue
        for k,v in df.iterrows():
            pattern = r'<a\s+.*?href="([^"]*http://nitter\.io\.lol/[^/]+/status/[^"]*)"[^>]*>'
            matches = re.findall(pattern, v['summary'])
            if len(matches)>0:
                if matches[0] in df['id'].values:
                    indices = df[df['id'] == matches[0]]
                    df.at[k, 'summary'] = re.sub(pattern,  "<blockquote>%s</blockquote>" % indices['summary'].values[0], v['summary'])
                    if 'i/lists' in user:
                        df=df.drop(indices.index)
                else:
                    oripost = sumPage(url=matches[0], raw=True)
                    quote = BeautifulSoup(oripost, 'html.parser').title.string.replace(" | nitter", '')
                    df.at[k,'summary'] = re.sub(pattern, "<blockquote>%s</blockquote>" % quote, v['summary'])
        df['content'] = df['published'].str[len('Sun, '):-len(' GMT')] +'['+df['author']+']'+'('+df['id'].str.replace(nitter,'x.com')+'): ' + df['summary']
        df.to_csv('test.csv', index=False)
        tweets=df['content'].to_csv().replace(nitter,'x.com')[:length]
        prompt=tweets+f"\n以上是一些推特节选，您是中文专栏『{info}最新资讯』的资深作者，请抽取『{info}』相关的信息，包括发推日期、作者(若有)、推特链接(若有)和推特内容，然后重新写成{lang}专栏文章，最后输出一篇用markdown排版的{lang}文章，如果没有{info}🇭🇰资讯请回复『NOT FOUND』"
        print('tweets:',prompt)
        if not 'NOT FOUND' in result:
            result=result+ask(prompt,model=model)
      if mail and len(result)>0:
        sendEmail(result)
      return result

# print(sumTweets('i/lists/1733652180576686386;elonmusk',minutes=600,mail=True))