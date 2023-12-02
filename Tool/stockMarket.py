import json
import os
import re
from concurrent.futures import ThreadPoolExecutor,wait
from copy import deepcopy
from urllib import parse
from config import MODEL
import pandas as pd
import requests
import time as t
import demjson3
from datetime import datetime
from Tool.llm import ask

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

def crawl_data_from_wencai(prompt:str='主板创业板,非ST，近20日涨停=1，成交额>5千万，近15日涨幅>0，换手率正序，不支持融资融券，动态市盈率，市盈率TTM，所属概念',model=MODEL):
    p=prompt.split('\n')
    question=p[0]
    headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
               'Accept-Encoding': 'gzip, deflate',
               'Accept-Language': 'zh-CN,zh;q=0.9',
               'Cache-Control': 'max-age=0',
               'Connection': 'keep-alive',
               'Upgrade-Insecure-Requests': '1',
               #   'If-Modified-Since': 'Thu, 11 Jan 2018 07:05:01 GMT',
               'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36'}

    headers_wc = deepcopy(headers)
    headers_wc["Referer"] = "http://www.iwencai.com/unifiedwap/unified-wap/result/get-stock-pick"
    headers_wc["Host"] = "www.iwencai.com"
    headers_wc["X-Requested-With"] = "XMLHttpRequest"

    Question_url = "http://www.iwencai.com/unifiedwap/unified-wap/result/get-stock-pick"

    payload = {
        "question": question,
        "perpage": 100,
        "query_type": "stock"
    }

    try:
        response = requests.get(Question_url, params=payload, headers=headers_wc)

        if response.status_code == 200:
            json = response.json()
            df = pd.DataFrame(json["data"]["data"])
            # 规范返回的columns，去掉[xxxx]内容,并将重复的命名为.1.2...
            cols = pd.Series([re.sub(r'\[[^)]*\]', '', col) for col in pd.Series(df.columns)])
            for dup in cols[cols.duplicated()].unique():
                cols[cols[cols == dup].index.values.tolist()] = [dup + '.' + str(i) if i != 0 else dup for i in range(sum(cols == dup))]
            df.columns=cols
            df['股票代码'] = df['股票代码'].str[7:] + df['股票代码'].str[:6]
            for c in ['最新价', '最新涨跌幅', 'a股市值(不含限售股)']:
                if c in cols.values:
                    df[c]=pd.to_numeric(df[c], errors='coerce')
            if len(p)>1 and len(p[1])>10:
                df=df[['股票简称', '股票代码','最新价', '最新涨跌幅', 'a股市值(不含限售股)','市盈率(pe)','市盈率(ttm)', '所属概念']]
                df['a股市值(不含限售股)']= df['a股市值(不含限售股)'].apply(lambda x:"%s亿"%(int(x/100000000)))
                return ask("『%s』\n%s"%(df.head(30).to_csv(index=False),p[1]),model)
            return df
        else:
            print("连接访问接口失败")
    except Exception as e:
        print(e)

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
def groupby2html(df:pd.DataFrame,key:str)->str:
    html_table = df.to_html(index=False)
    industry_summary = df.groupby(key).size().reset_index(name='Count')
    for i, row in industry_summary.iterrows():
        industry = row[key]
        count = row['Count']
        if f'<td rowspan={count}>{industry}</td>' not in html_table:
            if f'<td rowspan={count}>{industry}</td>' not in html_table:
                html_table = html_table.replace(f'<td>{industry}</td>', 'temp', 1)
                html_table = html_table.replace(f'<td>{industry}</td>', '')
                html_table = html_table.replace('temp', f'<td rowspan={count}>{industry}</td>', 1)
    return html_table

def uplimit10jqka(date:str='20231231'):
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
        ('date', date),
        ('order_field', '330329'),
        ('order_type', '0'),
        ('_', '1643899326926'),
    )
    response = requests.get('https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool',
                            headers={"user-agent": "Mozilla"}, params=params, cookies=cookies)
    result = response.json()['data']['info']
    df = pd.DataFrame(result)
    return df

def cnHotStockLatest(prompt:str='分类产业链',model = MODEL):
    idx=tencentK('sh000001')
    print(idx.index[-1].strftime('%Y%m%d'))
    df=uplimit10jqka(idx.index[-1].strftime('%Y%m%d'))
    df['currency_value'] = round(pd.to_numeric(df['currency_value'], errors='coerce') / 100000000)
    df['currency_value'] = df['currency_value'].astype(str).str[:] + '亿'
    df=df.fillna('')
    stockData='\n'.join(','.join(x) for x in df[['name', 'code', 'reason_type','high_days','currency_value']].values.tolist())
    result = ask('『%s』\n%s'%(stockData,prompt),model)
    return result