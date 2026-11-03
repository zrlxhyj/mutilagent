#加载模型
import os
from pathlib import Path
from dotenv import load_dotenv#加载配置文件.env的
from langchain.chat_models import init_chat_model

project_root=Path(__file__).resolve().parents[1]#拿到根目录路径
#Parh(__file__)是把路径转化为对象，然后调用对象的方法
# resolve()是绝对完整路径
# `parents` 是路径对象的**父目录序列（可迭代）**parents[0]是当前文件所在目录，parents[1]是当前文件所在目录的上级目录
load_dotenv(project_root/'.env')#加载.env文件

model_name=os.getenv('LLM_QWEN_MAX')#获取模型名称

if not model_name:
    raise ValueError("LLM_QWEN_MAX is not set in the environment variables.")
model=init_chat_model(model=model_name,model_provider=os.getenv('LLM_PROVIDER'))