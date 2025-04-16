import os
import json
from loguru import logger
from volcenginesdkarkruntime import Ark
from src.config import config

logger.add("logs/rag_process.log", rotation="1 MB", format="{time} {level} {message}")

class LLMClient:
    def __init__(self, user_id=None):
        # 默认使用系统配置
        self.user_id = user_id
        self.use_custom_keys = False
        
        # 初始化模型配置
        self._init_model_config()
    
    def _init_model_config(self):
        """初始化模型配置，优先使用用户自定义配置"""
        # 默认使用系统配置
        model_config = config['model']['generation']
        
        # 如果提供了用户ID，尝试加载用户自定义配置
        if self.user_id:
            user_settings = self._load_user_settings()
            if user_settings and user_settings.get('use_custom_keys', False):
                self.use_custom_keys = True
                if 'settings' in user_settings and 'generation' in user_settings['settings']:
                    model_config = user_settings['settings']['generation']
                    logger.info(f"使用用户自定义的生成模型配置: {model_config['provider']}")
        
        # 初始化API密钥
        if self.use_custom_keys:
            self.api_key = model_config.get('api_key', '')
            self.secret_key = model_config.get('secret_key', self.api_key)  # 对于某些API，secret_key可能与api_key相同
        else:
            # 使用系统环境变量中的密钥
            self.api_key = os.environ.get(model_config['api_key_env'])
            self.secret_key = os.environ.get(model_config.get('secret_key_env', model_config['api_key_env']))
        
        if not self.api_key:
            raise ValueError(f"未设置API密钥")
        
        # 初始化客户端和模型名称
        self.provider = model_config.get('provider', 'volcengine')
        self.model_name = model_config.get('model_name', 'doubao-1.5-pro-32k-250115')
        
        # 根据不同的提供商初始化客户端
        if self.provider == 'volcengine':
            self.client = Ark(ak=self.api_key, sk=self.secret_key)
        else:
            # 未来可以支持其他服务提供商的SDK初始化
            logger.warning(f"不支持的服务提供商: {self.provider}，使用默认的volcengine")
            self.client = Ark(ak=self.api_key, sk=self.secret_key)

    def _load_user_settings(self):
        """加载用户设置"""
        if not self.user_id:
            return None
        
        import os.path
        settings_path = self._get_user_settings_path()
        if not os.path.exists(settings_path):
            return None
        
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载用户设置失败: {str(e)}")
            return None
    
    def _get_user_settings_path(self):
        """获取用户设置文件路径"""
        import os
        project_root = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".."))
        settings_dir = os.path.join(project_root, "data", "user_settings")
        return os.path.join(settings_dir, f"{self.user_id}_model_settings.json")
    
    def generate(self, prompt, max_tokens=2000, max_retries=3):
        """调用 LLM 生成文本，添加重试机制"""
        logger.info(f"调用 LLM 生成文本，模型: {self.model_name}，提供商: {self.provider}")
        for attempt in range(max_retries):
            try:
                # volcengine 服务调用
                if self.provider == 'volcengine':
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        temperature=0.7
                    )
                    if response.choices:
                        generated_text = response.choices[0].message.content
                        logger.info(f"生成文本成功: {generated_text[:100]}...")
                        return generated_text
                    else:
                        logger.error("LLM 生成失败: 无响应内容")
                else:
                    # 未来可以支持其他服务提供商的API调用
                    logger.error(f"不支持的服务提供商: {self.provider}")
                    return None
            except Exception as e:
                logger.error(f"LLM 生成异常 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    logger.error("已达到最大重试次数，生成失败")
                    return None
        return None

if __name__ == "__main__":
    llm = LLMClient()
    prompt = "请生成一段关于洪水救援的描述。"
    result = llm.generate(prompt)
    if result:
        print(result)