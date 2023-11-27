import json
import os
import re
from concurrent.futures import ThreadPoolExecutor,wait
from urllib import parse
from config import KEYS
from litellm import completion
import pandas as pd
import requests
import time as t
import demjson3
from datetime import datetime
import io

def vikaData(id:str):
    headersVika = {
        'Authorization':'Bearer %s'%os.environ['VIKA'],
        'Connection': 'close'
    }
    vikaUrl = 'https://api.vika.cn/fusion/v1/datasheets/dstMiuU9zzihy1LzFX/records?viewId=viwoAJhnS2NMT&fieldKey=name'
    vikajson = requests.get(vikaUrl, headers=headersVika).json()
    print(vikajson)
    return [x['fields']['value'] for x in vikajson['data']['records'] if x['recordId'] == id][0]
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
            if max==0:
                max=df_data['max']
            print(df_data['page'],'/',df_data['max'],response.text[:99])
            df=pd.concat([df,df_data['df']])
        else:
            print("连接访问接口失败")
        if page==max:
            break
    df.to_csv('testwencai.csv',index=False,encoding='utf_8_sig')
    return df
def tencentK(mkt:str = '',symbol: str = "sh000001",period='day') -> pd.DataFrame:
    # symbol=symbol.lower()
    # A股的mkt为''
    if mkt=='us' and '.' not in symbol:
        symbolTxt=requests.get(f"http://smartbox.gtimg.cn/s3/?q={symbol}&t=us").text
        symbol = mkt + symbolTxt.split("~")[1].upper()
    elif mkt=='hk':
        symbol=mkt+symbol
    """
        腾讯证券-获取有股票数据的第一天, 注意这个数据是腾讯证券的历史数据第一天
        http://gu.qq.com/usQQQ.OQ/
        :param symbol: 带市场标识的股票代码
        :type symbol: str
        :return: 开始日期
        :rtype: pandas.DataFrame
        """
    headers = {"user-agent": "Mozilla", "Connection": "close"}
    url = "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?"
    if mkt=='us':
        url = "https://web.ifzq.gtimg.cn/appstock/app/usfqkline/get?"
    temp_df = pd.DataFrame()
    url_list=[]
    params = {
        "_var": f"kline_{period}qfq",
        "param": f"{symbol},{period},,,320,qfq",
        "r": "0.012820108110342066",
    }
    url_list.append(url + parse.urlencode(params))
    # print(url_list)
    with ThreadPoolExecutor(max_workers=10) as executor:  # optimally defined number of threads
        responeses = [executor.submit(getUrl, url) for url in url_list]
        wait(responeses)

    for res in responeses:
        text=res.result()
        try:
            inner_temp_df = pd.DataFrame(
                demjson3.decode(text[text.find("={") + 1:])["data"][symbol][period]
            )
        except:
            inner_temp_df = pd.DataFrame(
                demjson3.decode(text[text.find("={") + 1:])["data"][symbol]["qfq%s"%period]
            )
        temp_df = pd.concat([temp_df, inner_temp_df],ignore_index=True)

    if temp_df.shape[1] == 6:
        temp_df.columns = ["date", "open", "close", "high", "low", "amount"]
    else:
        temp_df = temp_df.iloc[:, :6]
        temp_df.columns = ["date", "open", "close", "high", "low", "amount"]
    temp_df.index = pd.to_datetime(temp_df["date"])
    del temp_df["date"]
    temp_df = temp_df.astype("float")
    temp_df.drop_duplicates(inplace=True)
    temp_df.rename(columns={'amount':'volume'}, inplace = True)
    # temp_df.to_csv('Quotation/'+symbol+'.csv',encoding='utf-8',index_label='date',date_format='%Y-%m-%d')
    return temp_df


def cnHotStock(prompt:str='''按炒作题材的产业链进行分类,在该csv最前面加上一列产业链，按产业链排序并输出csv''',iwcToken='',model='openai/gpt-3.5-turbo-1106'):
    idx = tencentK('sh000001')
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6,ja;q=0.5',
        'Cache-control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://www.iwencai.com',
        'Pragma': 'no-cache',
        'Referer': 'https://www.iwencai.com/unifiedwap/result?w=%E4%B8%BB%E6%9D%BF%E5%8F%8A%E5%88%9B%E4%B8%9A%E6%9D%BF%EF%BC%8C%E9%9D%9EST%EF%BC%8C%E8%BF%87%E5%8E%BB90%E6%97%A5%E6%B6%A8%E5%81%9C%E6%AC%A1%E6%95%B0%3E2%EF%BC%8C%E6%89%80%E5%B1%9E%E6%A6%82%E5%BF%B5%EF%BC%8C%E6%B5%81%E9%80%9A%E5%B8%82%E5%80%BC,%E9%87%8D%E8%A6%81%E4%BA%8B%E4%BB%B6%E5%86%85%E5%AE%B9&querytype=stock&addSign=1701007281531&sign=1701008018713',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'hexin-v': 'A1mRq-g0WKv1CgQ_uM_OAv5ebk425kyBN9txHXsO1ED-XnewwzZdaMcqgeYI',
        'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
    }
    data = {
        'query': '主板及创业板，非ST，过去90日涨停次数>2，所属概念，流通市值,重要事件内容',
        'urp_sort_way': 'desc',
        'urp_sort_index': '最新涨跌幅',
        'page': '1',
        'perpage': '100',
        'addheaderindexes': '',
        'condition': '[{"score":0.0,"chunkedResult":"主板_&_及创业板_&_非st_&_过去90日涨停次数>2_&_所属概念_&_流通市值_&_重要事件内容","opName":"and","opProperty":"","sonSize":6,"relatedSize":"0","logid":"84055bc7ade80b8b41d3327e010e6e86","source":"text2sql"},{"dateText":"","indexName":"上市板块","indexProperties":["包含主板>-<创业板"],"ci":true,"source":"text2sql","type":"index","indexPropertiesMap":{"包含":"主板>-<创业板"},"reportType":"null","ciChunk":"主板","createBy":"preCache","uiText":"上市板块包含主板,创业板","valueType":"_上市板块","domain":"abs_股票领域","sonSize":0,"dateList":[],"order":0},{"dateText":"","indexName":"股票简称","indexProperties":["不包含st"],"ci":true,"source":"text2sql","type":"index","indexPropertiesMap":{"不包含":"st"},"reportType":"null","ciChunk":"非st","createBy":"preCache","uiText":"股票简称不包含st","valueType":"_股票简称","domain":"abs_股票领域","sonSize":0,"dateList":[],"order":0},{"dateText":"近90日","indexName":"涨停次数","indexProperties":["(2","起始交易日期 %s","截止交易日期 %s"],"ci":true,"dateUnit":"日","source":"text2sql","type":"index","isDateRange":true,"indexPropertiesMap":{"(":"2","起始交易日期":"20230714","截止交易日期":"20231124"},"reportType":"TRADE_DAILY","ciChunk":"过去90日涨停次数>2","createBy":"ner_con","dateType":"+区间","isExtend":false,"uiText":"过去90日的涨停次数大于2","valueType":"_整型数值(次|个)","domain":"abs_股票领域","sonSize":0,"order":0},{"dateText":"近90日","indexName":"所属概念","indexProperties":[],"ci":true,"source":"text2sql","type":"index","indexPropertiesMap":{},"reportType":"null","ciChunk":"所属概念","createBy":"preCache","uiText":"所属概念","valueType":"_所属概念","domain":"abs_股票领域","sonSize":0,"dateList":[],"order":0},{"dateText":"","indexName":"a股市值(不含限售股)","indexProperties":["nodate 1","交易日期 20231124"],"ci":true,"dateUnit":"日","source":"text2sql","type":"index","indexPropertiesMap":{"交易日期":"20231124","nodate":"1"},"reportType":"TRADE_DAILY","ciChunk":"流通市值","createBy":"preCache","dateType":"交易日期","isExtend":false,"uiText":"a股市值(不含限售股)","valueType":"_浮点型数值(元)","domain":"abs_股票领域","sonSize":0,"dateList":[],"order":0},{"dateText":"","indexName":"重要事件内容","indexProperties":[],"ci":true,"source":"text2sql","type":"index","indexPropertiesMap":{},"reportType":"null","ciChunk":"重要事件内容","createBy":"preCache","uiText":"重要事件内容","valueType":"_重要事件内容","domain":"abs_股票领域","sonSize":0,"dateList":[],"order":0}]'%(idx.index[-1],idx.index[-90]),
        'codelist': '',
        'indexnamelimit': '',
        'ret': 'json_all',
        'source': 'Ths_iwencai_Xuangu',
        'date_range[0]': idx.index[-90],
        'date_range[1]': idx.index[-1],
        'iwc_token': iwcToken,
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
    df['股票代码'] = df['股票代码'].str[-2:]+df['股票代码'].str[:-3]
    df['重要事件公告时间'] = df.apply(lambda x: str(idx.index[idx.index.get_loc(datetime.strptime(x['重要事件公告时间'], '%Y%m%d'))-x['涨停次数']]), axis=1)
    df['重要事件内容'] = df['重要事件内容'].str.split('涨停原因：').apply(lambda x: x[-1].replace('。首板涨停。','') if x else '')
    df['区间振幅'] = round(pd.to_numeric(df['区间振幅'], errors='coerce'))
    df['区间振幅'] = df['区间振幅'].astype(str).str[:-2]+'%'
    df['a股市值(不含限售股)'] = round(pd.to_numeric(df['a股市值(不含限售股)'], errors='coerce') / 100000000)
    df['a股市值(不含限售股)'] = df['a股市值(不含限售股)'].astype(str).str[:-2]+'亿'
    df.to_csv('testwencai.csv',index=False,encoding='utf_8_sig')
    args=('股票简称','股票代码','重要事件公告时间','重要事件内容','a股市值(不含限售股)','区间振幅')
    df[list(args)].to_csv('testwencai.csv',index=False,encoding='utf_8_sig')
    stockData= '股票名称,代码,涨停日期,炒作题材,流通市值,区间振幅\n'+'\n'.join(''.join(x) for x in df.head(50)[list(args)].values.tolist())
    result = completion(
        model=model,
        messages=[{
            "role": "user",
            "content": '『%s』\n%s'%(stockData,prompt),
        }],
        api_key=KEYS[model])["choices"][0]["message"]["content"]
    return result


def cnHotStockLatest(prompt:str='分类产业链',model = 'openai/gpt-3.5-turbo-1106'):
    idx=tencentK('sh000001')
    print(idx.index[-1].strftime('%Y%m%d'))
    # print(idxdate.strftime('%Y%m%d'))
    cookies = {
        'Hm_lvt_78c58f01938e4d85eaf619eae71b4ed1': '1640619309,1642582805',
        'hxmPid': '',
        'v': 'A3mxy4iUODTC-eSfUy3u4h6-ju5Whm-wV3iRo5uu9LIe4ZcQ49Z9COfKoYIo',
    }
    params = (
        ('page', '1'),
        ('limit', '1600'),
        ('field', '199112,10,9001,330323,330324,330325,9002,330329,133971,133970,1968584,3475914,9003,9004'),
        ('filter', 'HS,GEM2STAR'),
        ('date', idx.index[-1].strftime('%Y%m%d')),
        ('order_field', '330329'),
        ('order_type', '0'),
        ('_', '1643899326926'),
    )
    response = requests.get('https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool',headers={"user-agent": "Mozilla"}, params=params, cookies=cookies)
    result=response.json()['data']['info']
    df=pd.DataFrame(result)
    df['currency_value'] = round(pd.to_numeric(df['currency_value'], errors='coerce') / 100000000)
    df['currency_value'] = df['currency_value'].astype(str).str[:] + '亿'
    df=df.fillna('')
    stockData='\n'.join(','.join(x) for x in df[['name', 'code', 'reason_type','high_days','currency_value']].values.tolist())
    result = completion(model=model, messages=[{
            "role": "user",
            "content": '『%s』\n%s'%(stockData,prompt),
        }], api_key=KEYS[model])["choices"][0]["message"]["content"]
    return result

# if __name__=='__main__':
#     df=pd.read_csv(io.StringIO(cnHotStock(iwcToken='0ac9665217010766879282200')))
#     print(df)