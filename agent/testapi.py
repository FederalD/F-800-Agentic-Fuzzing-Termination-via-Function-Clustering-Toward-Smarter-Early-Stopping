import os
import json
from langchain.tools import tool
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

# =============================================
# 初始化 LLM - 使用新的API端点
# =============================================
'''
llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api2.aigcbest.top/v1",
    api_key="XXXX",
    temperature=0.7
)
'''

from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com/v1",
    api_key="XXXX",
)

print(llm.invoke("hello").content)
