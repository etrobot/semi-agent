import ast
import datetime
import json
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

def ask(prompt:str):
    return completion(model=MODEL, messages=[{
        "role": "user",
        "content": prompt,
    }], api_key=KEYS[MODEL])["choices"][0]["message"]["content"]

def genPost(prompt:str):
  prompt+='''\n\nTurn texts above to a blog post,output python dict format:{
    "title":"title",
    "tags":["tag1","tag2",...],
    "post":"""markdown"""
  }
  '''
  text=ask(prompt)
  if not 'openai' in MODEL:
      text='{' + text.split('{')[-1].split('}')[0] + '}'
  result=ast.literal_eval(text)
  title,tags,post=result['title'],result['tags'], result['post'].replace('  ','')
  # filename="-".join([p[0] for p in pinyin(string, style=Style.NORMAL)])
  template = '''
---
title: "{title}"
date: {date}
draft: true
tags: {tags}
author: {author}
category: {cate}
---\n
{post}\n\n
        '''.format(
        title=title,
        date=datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'),
        tags=str(tags),
        cate='AGENTs',
        author='Frank Lin',
        post=post,
    )
  return template