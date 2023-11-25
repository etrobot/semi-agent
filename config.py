import os
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

KEYS={
    "palm/text-bison-001":os.environ['PALM_API_KEY'],
    "openai/gpt-3.5-turbo-1106":os.environ['OPENAI_API_KEY']
}

MODEL=os.environ['MODEL']

STEPCOLS = ['stepId', 'fromId', 'recursion', 'prompt', 'LLMgen', 'cmdIsAdded', 'status', 'remark']
DBPATH='agentProject%s.csv'%int(datetime.now().timestamp())

SEARCHSITE = 'site:news.yahoo.com'