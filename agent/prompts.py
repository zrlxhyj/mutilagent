from pathlib import Path
import yaml

def load_yaml(file_path):
    """Load a YAML file and return its contents as a dictionary."""
    with open(file_path, 'r', encoding='utf-8') as file:
        result = yaml.safe_load(file)
        if not isinstance(result, dict):
            raise ValueError(f"YAML file {file_path} 不是字典类型.")#必须是字典类型
    return result

root_path=Path(__file__).resolve().parents[1]  # 获取项目根目录路径
yaml_file_path = root_path / 'prompt' / 'prompts.yml'  # 构建 YAML 文件路径
config=load_yaml(yaml_file_path)  # 加载 YAML 文件内容
main_agent_content=config["main_agent"]  # 获取 main_agent_content 的内容
sub_agent_content=config["sub_agents"]  # 获取 sub_agents 的内容

