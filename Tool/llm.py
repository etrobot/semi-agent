from config import MODEL,KEYS
from litellm import completion
def summarize(text:str):
    print(len(text))
    return completion(model=MODEL, messages=[{
        "role": "user",
        "content": '『%s』TLDR;'%text,
    }], api_key=KEYS[MODEL])["choices"][0]["message"]["content"]

def makelist(prompt:str,subList=False):
    suffix =' Output keypoints with index'
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