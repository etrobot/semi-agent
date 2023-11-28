import re
from config import MODEL
from Tool.textDealer import letterNnum
from Tool.llm import genPlan
import pandas as pd
import numpy as np
def run(filename:str):
  input('Input anything and hit Enter to Run when finishing plan sheet editing: ')
  df=pd.read_csv(filename).dropna(subset=['Prompt','Agent'])
  for k,v in df.iterrows():
    if v['Skip'] == 'Y':
      continue
    prompt=v['Prompt']
    pos = re.findall(r"\{\{(.*?)\}\}",prompt)
    for p in pos:
      letter,num=letterNnum(p)
      prompt=prompt.replace(p,df[letter].values[num-1])
    print('Step',k,prompt)
    model=v['Model']
    if model is None or model=='' or np.isnan(model):
      model=MODEL
    result=eval(v['Agent'])(prompt,model)
    df.at[k,'Conclusion']=str(result)
    df.to_csv(filename, index=False, encoding='utf_8_sig')

if __name__=='__main__':
  #you can use run(filename) to run the existing plan csv
  run(genPlan('write a news post about MSFT and OpenAI'))