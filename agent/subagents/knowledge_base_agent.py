from agent.prompts import sub_agent_content
from tools.ragflow_tools import ask_knowledge_base

settings=sub_agent_content["ragflow"]  # 获取市场情报助手的配置
sub_agent_name=settings["name"]
sub_agent_description=settings["description"]
sub_agent_system_prompt=settings["system_prompt"]

ask_knowledge_agent = {
    "name": sub_agent_name,
    "description": sub_agent_description,
    "system_prompt": sub_agent_system_prompt,
    "tools": [ask_knowledge_base],}