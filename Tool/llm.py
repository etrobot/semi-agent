import ast
import datetime
import json
import os

import pandas as pd
from config import MODEL,KEYS
from litellm import completion

def ask(prompt:str,model=MODEL):
    if 'API_BASE_URL' in os.environ.keys() and 'openai' in model:
        return completion(model=model, messages=[{"role": "user","content": prompt,}], api_key=KEYS[model],
                          api_base=os.environ['API_BASE_URL'])["choices"][0]["message"]["content"]
    return completion(model=model, messages=[{"role": "user", "content": prompt, }], api_key=KEYS[model])["choices"][0]["message"]["content"]

def summarize(text:str,model=MODEL):
    print(len(text))
    if len(text)<100:
        return text
    return ask('『%s』TLDR;'%text,model=model)

def make_list(prompt:str,subList=False,model=MODEL):
    suffix =' Output points with index'
    if subList:
        suffix=' and output "\nkeyword1 keyword2 keyword3\nkeyword4 keyword5 keyword6\n...",do not output any punctuation or symbol'
    reply_text = ask(prompt + suffix,model=model)
    print(reply_text.split('\n'))
    return [x for x in reply_text.split('\n') if len(x)>2 and sum(int(y in x) for y in prompt)>0]

def genPost(prompt:str,category='INFO',model=MODEL):
  prompt+='''\n\nTurn texts above to a blog post,output python dict format:{
    "title":"title",
    "tags":["tag1","tag2",...],
    "post":"""markdown"""
  }
  '''
  text=ask(prompt,model=model)
  text='{' + text.split('{')[-1].split('}')[0] + '}'
  result=ast.literal_eval(text)
  title,tags,post=result['title'],result['tags'], result['post'].replace('  ','')
  # filename="-".join([p[0] for p in pinyin(string, style=Style.NORMAL)])
  template = '''---
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
        cate=category,
        author='Frank Lin',
        post=post,
    )
  return template

def genPlan(prompt:str,model=MODEL)->str:
    prompt+='''
    for this mission,make steps of thoughts with json format like{
    "steps":[
        {"step":1,"thought":"get info about","tool":"search"},
        {"step":2,"thought":"{{Conclusion 1}} summary","tool":"summarize"},
        ...
    ]},the tools are search/summarize/make_list and just can use one tool every step, dont add any other tool.
    '''
    text = ask('Mission:'+prompt,model=model)
    print(text)
    try:
        text = '{' + '}'.join('{'.join(text.split('{')[1:]).split('}')[:-1]) + '}'
        print(text)
    except Exception as e:
        print(e)
    text2json=json.loads(text)
    df=pd.DataFrame(text2json['steps']).sort_values(['step'])
    df=df.drop('step', axis=1)
    df.columns=['Prompt','Agent']
    df['Conclusion']=''
    df['Skip']=''
    for k,v in df.iterrows():
        if k>0:
            df.at[k,'Prompt']='{{Conclusion %s}}'%(k+1)+v['Prompt']
    filename='agentMission%s.csv'%datetime.datetime.now().strftime('%Y%m%d-%H_%M')
    df.to_csv(filename, index=False, encoding='utf_8_sig')
    return filename