import os
from config import STEPCOLS,DBPATH
from Tool.browse import search
from Tool.filesystem import genHtml
import uuid
import pandas as pd
from Tool.llm import makelist

def analyze(df:pd.DataFrame,prompt:str='plz ouput keypoints with index',recursion_count:int = 0,fromId:str=None)->bool:
    #get plan(read database) or gen and write plan to database
    details=makelist(prompt)
    rows=[[str(uuid.uuid4()),fromId,recursion_count,x,search(target+' '+x),False,'',''] for x in details]
    print('rows',rows)
    df=pd.concat([df,pd.DataFrame(rows,columns=STEPCOLS)])
    df.to_csv(DBPATH,index=False,encoding='utf_8_sig')
    genHtml(df)
    return True

def useTool(tool='search',prompt='plan'):
    return eval(tool)(prompt)

def query(prompt:str, recursion_count: int = 1,fromId:str=None,stepId:str=None):
    if recursion_count > 2:
        return
    if os.path.isfile(DBPATH):
        df=pd.read_csv(DBPATH)
    else:
        df=pd.DataFrame(data=[],columns=STEPCOLS)
    print('query prompt:',prompt)
    toolwork = useTool(tool='search', prompt=target+' '+prompt)
    analyze(df,toolwork,recursion_count,fromId)
    df = pd.read_csv(DBPATH)
    details = df.loc[df['fromId']==fromId]
    print('details:\n',details)
    # input('break %s:'%fromId)
    for k,v in details.iterrows():
        if stepId is not None and v['stepId']!=stepId:
            continue
        query(v['LLMgen'], recursion_count+1,fromId=v['stepId'])

if __name__=='__main__':
    target = 'MSFT'
    query(f'Analyze the investment value of {target} from the technical, fundamental and news aspects',fromId=str(uuid.uuid4()))
