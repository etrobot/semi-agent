# Semi-Agent
### a simple AI Agent framework

## Flow
* Ask LLM to generate plan schedule with prompts and tool to use
* Schedule management is so easy, you can connect or skip step or modify prompts with table software like Excel/Google Sheets
* You can add any tool or agent by writing python scripts freely

## Use Table Software as GUI
* [Example Sheet >>>](https://docs.google.com/spreadsheets/d/1piAvmWc_-5mVxMqRDOBirWC08NGoiQ5THpKntcE-md0/edit?usp=sharing)


![Google Sheets as GUI](https://github.com/etrobot/semi-agent/assets/3889058/68848daf-329c-49d3-9a21-c8d055ad3f46)

## How to use
* ```pip install -r requirements.txt```
* create a .env file manually at project folder root. add the model and key like:
```
MODEL="openai/gpt-3.5-turbo-1106"
OPENAI_API_KEY="sk-..."
``` 
* or
```
MODEL="palm/text-bison-001"
PALM_API_KEY="AI..."
```
* run main.py

## Try it on Google Colab

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1efxYRVsC_b4a1E2Mqz6qX3cDy9YNnJNL?usp=sharing)