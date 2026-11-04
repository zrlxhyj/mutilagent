#完成子agent的搜索功能
from agent.prompts import sub_agent_content
from tools.tavily_tools import internet_search

settings=sub_agent_content["tavily"]  # 获取市场情报助手的配置
sub_agent_name=settings["name"]
sub_agent_description=settings["description"]
sub_agent_system_prompt=settings["system_prompt"]

network_search_agent = {
    "name": sub_agent_name,
    "description": sub_agent_description,
    "system_prompt": sub_agent_system_prompt,
    "tools": [internet_search],}