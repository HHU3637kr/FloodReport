import os
import yaml

def load_config(config_path=None):
    if config_path is None:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        config_path = os.path.join(root_dir, "config", "rag_config.yaml")
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_template(template_path=None):
    if template_path is None:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        template_path = os.path.join(root_dir, "config", "report_template.yaml")
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"模板文件 {template_path} 不存在")
    with open(template_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# 加载默认配置和模板
config = load_config()
default_template = load_template()