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
def sumPage(url: str,model=MODEL) -> str:
    print('Sum:',url)
    headers = {
        'accept-language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6,ja;q=0.5',
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Mobile Safari/537.36"
    }
    session = requests.Session()
    session.headers = headers
    if url.startswith('https://twitter.com'):
        url=url.replace('https://twitter.com','https://nitter.net')
    try:
        response = session.get(url)
        print(response.text[:100])
        soup = BeautifulSoup(response.text, 'html.parser')

        elements = [
            element.text for element in soup.find_all(["title","h1", "h2", "h3","li","p"])
            if len(element.text) > 5
        ]
        txt=' '.join(elements)
        return summarize(txt,model)

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

def sumTweets(user:str='elonmusk',info:str='人工智能',lang:str='中文',ingores:str="webinar",length:int=4000,nitter='nitter.io.lol',model=MODEL):
    rss_url=f'https://{nitter}/{user}/rss'
    df=get_rss_df(rss_url)
    df['conent']=df['published'].str[len('Sun, '):-len(' 06:20:57 GMT')]+df['author']+df['summary']
    tweets=df['conent'].to_csv().replace(nitter,'x.com')[:length]
    prompt=tweets+f"\n以上是一些推特节选，而你是中文专栏『{info}最新资讯』的资深作者，忽略推中的『{user}，{ingores}』的自我宣传和重复的信息，抽取『{info}』相关的信息，含发推日期、@作者(若有)和链接(若有)，并重新写成{lang}专栏文章，最后输出一篇用markdown排版的{lang}文章"
    print('tweets:',prompt)
    result=ask(prompt,model=model)
    return result

# print(sumTweets('i/lists/1733652180576686386'))
