import pandas as pd
def genHtml(data:pd.DataFrame):
    # 创建一个空字符串，用于存储转换后的嵌套div
    nested_div = ''

    # 遍历每行数据
    for k,v in data.iterrows():
      id_val, content_val, parent_val = v['stepId'],v['LLMgen'],v['fromId']

      # 创建div元素，并包含id和content
      div_element = f'<div id="{id_val}" class="child">{content_val}</div>'

      # 检查是否有父节点
      if pd.notna(parent_val):
          # 将当前div元素插入父节点的内部
          parent_div = f'<div id="{parent_val}" class="child">'
          nested_div = nested_div.replace(parent_div, parent_div + div_element)

    htmlcontent='''
<head>
<style>
	div{
		margin: auto;
		padding:10px;
	}
	body{
		background-color:black;
		color:#b1b1b1;
	}
	.child {
		border: 1px solid gray;
		float: right;
		width: 50%;
	}
</style>
<title>Nested Table</title>
</head>
<body>
%s
</body>
    '''%nested_div

    # 将嵌套div字符串写入HTML文件
    with open('UI.html', 'w') as file:
      file.write(htmlcontent)
