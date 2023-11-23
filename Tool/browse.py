import os
import time as t
import json
import requests
from bs4 import BeautifulSoup
from requests.cookies import RequestsCookieJar
from Tool.llm import summarize,makelist
from duckduckgo_search import DDGS
from config import SEARCHSITE

def sumPage(url: str) -> str:
    print('Sum:',url)
    def dealCookies(cookies):
        cookie_jar = RequestsCookieJar()
        for cookie in cookies:
            cookie_jar.set(cookie['name'], cookie['value'], domain=cookie['domain'], path=cookie['path'],
                           secure=cookie['secure'])
        return cookie_jar

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Mobile Safari/537.36"
    }

    session = requests.Session()
    session.headers = headers
    try:
      cookies = dealCookies(json.load(open('cookies.json')))
      session.cookies.update(cookies)
    except Exception as e:
      print(e)
      pass

    try:
        response = session.get(url)
        print(response.text[:100])
        soup = BeautifulSoup(response.text, 'html.parser')

        elements = [
            element.text for element in soup.find_all(["h1", "h2", "h3", "p"])
            if len(element.text) > 5
        ]
        txt=' '.join(elements)
        return txt

    except Exception as e:
        print(e)
        return ''

def search(prompt:str)->str:
    details=[prompt]
    print(details)
    if len(prompt)>50:
        prompt = f'I want to search this info:『{prompt}』,plz make several groups of keywords'
        details = makelist(prompt,subList=True)
    final=[]
    if 'SOCKSPROXY' in os.environ.keys():
        ddgs = DDGS(proxies = os.environ['SOCKSPROXY'])
    else:
        ddgs = DDGS()
    for words in details[:5]:
        print('search:',words)
        serp=ddgs.text(SEARCHSITE+' '+str(words), max_results=1)
        links=[r['href'] for r in serp]
        print('search result:',links)
        pageSum ='\n'.join(sumPage(link) for link in links)
        if len(pageSum)<200:
            sumSum = pageSum
        else:
            sumSum = summarize(pageSum)
        print('sumSum:',sumSum)
        final.append(sumSum)
        t.sleep(30)#ddg limit
    return '\n'.join(makelist('\n'.join(final)))