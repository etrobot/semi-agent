import re

import requests
from bs4 import BeautifulSoup

from config import MODEL,KEYS
from litellm import completion
def summarize(text:str):
    print(len(text))
    return completion(model=MODEL, messages=[{
        "role": "user",
        "content": '『%s』TLDR;'%text,
    }], api_key=KEYS[MODEL])["choices"][0]["message"]["content"]

def makelist(prompt:str,subList=False):
    suffix =' Output points with index'
    if subList:
        suffix=' and output "\nkeyword1 keyword2 keyword3\nkeyword4 keyword5 keyword6\n...",do not output any punctuation or symbol'
    msg = [{
        "role": "user",
        "content": prompt + suffix,
    }]
    print('with suffix:',prompt + suffix)
    response = completion(model=MODEL, messages=msg, api_key=KEYS[MODEL])
    reply_text = response["choices"][0]["message"]["content"]
    print(reply_text.split('\n'))
    return [x for x in reply_text.split('\n') if len(x)>2]

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
    return queryText
def ask(prompt:str):
    return completion(model=MODEL, messages=[{
        "role": "user",
        "content": prompt,
    }], api_key=KEYS[MODEL])["choices"][0]["message"]["content"]

if __name__=='__main__':
    print(wechatPost('https://mp.weixin.qq.com/s/fVTxYWc4f2x9W710mMQzJA'))