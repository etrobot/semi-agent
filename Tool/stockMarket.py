import json
import re
from copy import deepcopy
from datetime import datetime
from urllib import parse
from config import MODEL,KEYS
from litellm import completion
import pandas as pd
import requests
import time as t

def getUrl(url,cookie=''):
    retryTimes = 0
    while retryTimes < 99:
        try:
            response = requests.get(url,headers={"user-agent": "Mozilla", "cookie": cookie,"Connection":"close"},timeout=5)
            return response.text
        except Exception as e:
            print(e.args)
            print('retrying.....')
            t.sleep(60)
            retryTimes += 1
            continue

def parse_wencai(response:json):
    json = response["answer"]["components"][0]["data"]
    max = int(int(json["meta"]['extra']['row_count']) / 100) + 1
    page = int(json["meta"]['page'])
    df_data = pd.DataFrame(json["datas"])
    cols = pd.Series([re.sub(r'\[[^)]*\]', '', col) for col in pd.Series(df_data.columns)])
    df_data.columns = cols
    return {'page':page,'max':max,'df':df_data}
def crawl_data_from_wencai(headers:dict,data:dict):
    max=0
    page=0
    df=pd.DataFrame()
    while page<99:
        page+=1
        data['page']=page
        response = requests.post('https://www.iwencai.com/gateway/urp/v7/landing/getDataList', headers=headers, data=data)
        if response.status_code == 200:
            df_data=parse_wencai(response.json())
            print(df_data['page'],'/',df_data['max'])
            if max==0:
                max=df_data['max']
            df=pd.concat([df,df_data['df']])
        else:
            print("连接访问接口失败")
        if page==max:
            break
    df.to_csv('testwencai.csv',index=False,encoding='utf_8_sig')
    return df
def cmsK(code:str,type:str='daily'):
    """招商证券A股行情数据"""
    typeNum={'daily':1,'monthly':3,'weekly':2}
    code=code.upper()
    quoFile = 'Quotation/' + code + '.csv'
    if len(code)==8:
        code = code[:2] + ':'+code[2:]
    params = (
        ('funcno', 20050),
        ('version', '1'),
        ('stock_list', code),
        ('count', '10000'),
        ('type', typeNum[type]),
        ('field', '1:2:3:4:5:6:7:8:9:10:11:12:13:14:15:16:18:19'),
        ('date', datetime.now().strftime("%Y%m%d")),
        ('FQType', '2'),#不复权1，前复权2，后复权3
    )
    url='https://hq.cmschina.com/market/json?'+parse.urlencode(params)
    kjson=json.loads(getUrl(url))
    if 'results' not in kjson.keys() or  len(kjson['results'])==0:
        return []
    data = kjson['results'][0]['array']
    df=pd.DataFrame(data=data,columns=['date','open','high','close','low','yesterday','volume','amount','price_chg','percent','turnoverrate','ma5','ma10','ma20','ma30','ma60','afterAmt','afterVol'])
    df.set_index('date',inplace=True)
    df.index=pd.to_datetime(df.index,format='%Y%m%d')
    df=df.apply(pd.to_numeric, errors='coerce').fillna(df)
    if type=='daily':
        df.to_csv(quoFile,encoding='utf-8',index_label='date',date_format='%Y-%m-%d')
    df['percent']=df['percent'].round(4)
    return df

def cnHotStock(prompt:str='按炒作题材的产业链进行分类，选出炒作时间跨度最长的10个产业链(注明起止日期),并列出包含个股(含代码和市值)'):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6,ja;q=0.5',
        'Cache-control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://www.iwencai.com',
        'Pragma': 'no-cache',
        'Referer': 'https://www.iwencai.com/unifiedwap/result?w=%E4%B8%BB%E6%9D%BF%E5%8F%8A%E5%88%9B%E4%B8%9A%E6%9D%BF%EF%BC%8C%E9%9D%9EST%EF%BC%8C%E8%BF%87%E5%8E%BB90%E6%97%A5%E6%B6%A8%E5%81%9C%E6%AC%A1%E6%95%B0%3E2%EF%BC%8C%E6%89%80%E5%B1%9E%E6%A6%82%E5%BF%B5%EF%BC%8C%E6%B5%81%E9%80%9A%E5%B8%82%E5%80%BC,%E9%87%8D%E8%A6%81%E4%BA%8B%E4%BB%B6%E5%86%85%E5%AE%B9&querytype=stock',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'hexin-v': 'AyTsTI0PHcV-bWm6qOvrbfO18ykTvVrECq7UGz9lsfyy9MoXZs0Yt1rxrdaN',
        'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
    }
    data = {
        'query': '主板及创业板，非ST，过去90日涨停次数>2，所属概念，流通市值,重要事件内容',
        'urp_sort_way': 'desc',
        'urp_sort_index': '最新涨跌幅',
        'page': '15',
        'perpage': '100',
        'addheaderindexes': '',
        'condition': '[{"score":0.0,"chunkedResult":"主板_&_及创业板_&_非st_&_过去90日涨停次数>2_&_所属概念_&_流通市值_&_重要事件内容","opName":"and","opProperty":"","sonSize":6,"relatedSize":"0","logid":"84055bc7ade80b8b41d3327e010e6e86","source":"text2sql"},{"dateText":"","indexName":"上市板块","indexProperties":["包含主板>-<创业板"],"ci":true,"source":"text2sql","type":"index","indexPropertiesMap":{"包含":"主板>-<创业板"},"reportType":"null","ciChunk":"主板","createBy":"preCache","uiText":"上市板块包含主板,创业板","valueType":"_上市板块","domain":"abs_股票领域","sonSize":0,"dateList":[],"order":0},{"dateText":"","indexName":"股票简称","indexProperties":["不包含st"],"ci":true,"source":"text2sql","type":"index","indexPropertiesMap":{"不包含":"st"},"reportType":"null","ciChunk":"非st","createBy":"preCache","uiText":"股票简称不包含st","valueType":"_股票简称","domain":"abs_股票领域","sonSize":0,"dateList":[],"order":0},{"dateText":"近90日","indexName":"涨停次数","indexProperties":["(2","起始交易日期 20230714","截止交易日期 20231124"],"ci":true,"dateUnit":"日","source":"text2sql","type":"index","isDateRange":true,"indexPropertiesMap":{"(":"2","起始交易日期":"20230714","截止交易日期":"20231124"},"reportType":"TRADE_DAILY","ciChunk":"过去90日涨停次数>2","createBy":"ner_con","dateType":"+区间","isExtend":false,"uiText":"过去90日的涨停次数大于2","valueType":"_整型数值(次|个)","domain":"abs_股票领域","sonSize":0,"order":0},{"dateText":"近90日","indexName":"所属概念","indexProperties":[],"ci":true,"source":"text2sql","type":"index","indexPropertiesMap":{},"reportType":"null","ciChunk":"所属概念","createBy":"preCache","uiText":"所属概念","valueType":"_所属概念","domain":"abs_股票领域","sonSize":0,"dateList":[],"order":0},{"dateText":"","indexName":"a股市值(不含限售股)","indexProperties":["nodate 1","交易日期 20231124"],"ci":true,"dateUnit":"日","source":"text2sql","type":"index","indexPropertiesMap":{"交易日期":"20231124","nodate":"1"},"reportType":"TRADE_DAILY","ciChunk":"流通市值","createBy":"preCache","dateType":"交易日期","isExtend":false,"uiText":"a股市值(不含限售股)","valueType":"_浮点型数值(元)","domain":"abs_股票领域","sonSize":0,"dateList":[],"order":0},{"dateText":"","indexName":"重要事件内容","indexProperties":[],"ci":true,"source":"text2sql","type":"index","indexPropertiesMap":{},"reportType":"null","ciChunk":"重要事件内容","createBy":"preCache","uiText":"重要事件内容","valueType":"_重要事件内容","domain":"abs_股票领域","sonSize":0,"dateList":[],"order":0}]',
        'codelist': '',
        'indexnamelimit': '',
        'logid': '84055bc7ade80b8b41d3327e010e6e86',
        'ret': 'json_all',
        'sessionid': '84055bc7ade80b8b41d3327e010e6e86',
        'source': 'Ths_iwencai_Xuangu',
        'date_range[0]': '20230714',
        'date_range[1]': '20231124',
        'iwc_token': '0ac9665017008739185682997',
        'urp_use_sort': '1',
        'user_id': 'Ths_iwencai_Xuangu_v2a4cbw2do7nutkf3col1omxv3jpguts',
        'uuids[0]': '24087',
        'query_type': 'stock',
        'comp_id': '6836372',
        'business_cat': 'soniu',
        'uuid': '24087',
    }
    df = crawl_data_from_wencai(headers,data)
    for col in ['a股市值(不含限售股)','区间振幅','涨停次数']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df=df.sort_values(by=['区间振幅','涨停次数','a股市值(不含限售股)'],ascending=False)
    df=df[df['重要事件名称']=='涨停'].drop_duplicates(subset=['股票代码'])
    df['股票代码']=df['股票代码'].str[-2:]+df['股票代码'].str[:-3]
    df['重要事件内容'] = df['重要事件内容'].str.split('涨停原因：').apply(lambda x: x[-1].replace('。首板涨停。','') if x else '')
    df['a股市值(不含限售股)'] = round(pd.to_numeric(df['a股市值(不含限售股)'], errors='coerce') / 100000000)
    df['a股市值(不含限售股)'] = df['a股市值(不含限售股)'].astype(str)+'亿'
    df.to_csv('testwencai.csv',index=False,encoding='utf_8_sig')
    args=('股票简称','股票代码','重要事件公告时间','重要事件内容','a股市值(不含限售股)')
    df[list(args)].to_csv('testwencai.csv',index=False,encoding='utf_8_sig')
    stockData= '股票名称,代码,涨停日期,炒作题材,流通市值\n'+'\n'.join(''.join(x) for x in df.head(50)[list(args)].values.tolist())
    return completion(model=MODEL, messages=[{
        "role": "user",
        "content": '『%s』\n%s'%(stockData,prompt),
    }], api_key=KEYS[MODEL])["choices"][0]["message"]["content"]

if __name__=='__main__':
    stocks=cnHotStock()
    print(stocks)
