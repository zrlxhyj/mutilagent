#完成子agent的搜索功能
from agent.prompts import sub_agent_content
from tools.db_tools import execute_limit_sql,list_curr_table,get_table_data

settings=sub_agent_content["db"]  # 获取市场情报助手的配置
sub_agent_name=settings["name"]
sub_agent_description=settings["description"]
sub_agent_system_prompt=settings["system_prompt"]

database_query_agent = {
    "name": sub_agent_name,
    "description": sub_agent_description,
    "system_prompt": sub_agent_system_prompt,
    "tools": [execute_limit_sql,list_curr_table,get_table_data],}