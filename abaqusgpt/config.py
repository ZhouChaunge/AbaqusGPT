"""Configuration management for AbaqusGPT."""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Config(BaseModel):
    """Application configuration."""
    
    # ===========================================
    # Default LLM Settings
    # ===========================================
    default_model: str = os.getenv("DEFAULT_MODEL", "gpt-4o")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    timeout: int = int(os.getenv("LLM_TIMEOUT", "60"))
    max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
    
    # ===========================================
    # International Providers
    # ===========================================
    
    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_api_base: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    
    # Anthropic
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Ollama (Local)
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # ===========================================
    # Chinese LLM Providers / 国产大模型
    # ===========================================
    
    # 智谱 AI (GLM)
    zhipu_api_key: str = os.getenv("ZHIPU_API_KEY", "")
    
    # 通义千问 (Qwen / DashScope)
    dashscope_api_key: str = os.getenv("DASHSCOPE_API_KEY", "")
    
    # DeepSeek
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    
    # 百度文心一言 (ERNIE)
    baidu_api_key: str = os.getenv("BAIDU_API_KEY", "")
    baidu_secret_key: str = os.getenv("BAIDU_SECRET_KEY", "")
    
    # 讯飞星火 (Spark)
    spark_app_id: str = os.getenv("SPARK_APP_ID", "")
    spark_api_key: str = os.getenv("SPARK_API_KEY", "")
    spark_api_secret: str = os.getenv("SPARK_API_SECRET", "")
    
    # 月之暗面 Kimi (Moonshot)
    moonshot_api_key: str = os.getenv("MOONSHOT_API_KEY", "")
    
    # MiniMax
    minimax_api_key: str = os.getenv("MINIMAX_API_KEY", "")
    minimax_group_id: str = os.getenv("MINIMAX_GROUP_ID", "")
    
    # 零一万物 (Yi)
    yi_api_key: str = os.getenv("YI_API_KEY", "")
    
    # 百川智能 (Baichuan)
    baichuan_api_key: str = os.getenv("BAICHUAN_API_KEY", "")
    
    # 阶跃星辰 (StepFun)
    stepfun_api_key: str = os.getenv("STEPFUN_API_KEY", "")
    
    # 字节豆包 (Volcengine)
    volcengine_api_key: str = os.getenv("VOLCENGINE_API_KEY", "")
    volcengine_endpoint_id: str = os.getenv("VOLCENGINE_ENDPOINT_ID", "")
    
    # 腾讯混元 (Hunyuan)
    tencent_secret_id: str = os.getenv("TENCENT_SECRET_ID", "")
    tencent_secret_key: str = os.getenv("TENCENT_SECRET_KEY", "")
    
    # 商汤日日新 (SenseNova)
    sensenova_api_key: str = os.getenv("SENSENOVA_API_KEY", "")
    
    # 昆仑万维天工 (SkyWork)
    skywork_api_key: str = os.getenv("SKYWORK_API_KEY", "")
    
    # 硅基流动 (SiliconFlow)
    siliconflow_api_key: str = os.getenv("SILICONFLOW_API_KEY", "")
    
    # ===========================================
    # Paths
    # ===========================================
    knowledge_base_path: Path = Path(__file__).parent.parent / "knowledge_base"
    
    def get_available_providers(self) -> list[str]:
        """Return list of configured (available) providers."""
        providers = []
        
        if self.openai_api_key:
            providers.append("openai")
        if self.anthropic_api_key:
            providers.append("anthropic")
        if self.zhipu_api_key:
            providers.append("zhipu")
        if self.dashscope_api_key:
            providers.append("dashscope")
        if self.deepseek_api_key:
            providers.append("deepseek")
        if self.baidu_api_key and self.baidu_secret_key:
            providers.append("baidu")
        if self.spark_app_id and self.spark_api_key:
            providers.append("spark")
        if self.moonshot_api_key:
            providers.append("moonshot")
        if self.minimax_api_key:
            providers.append("minimax")
        if self.yi_api_key:
            providers.append("yi")
        if self.baichuan_api_key:
            providers.append("baichuan")
        if self.stepfun_api_key:
            providers.append("stepfun")
        if self.volcengine_api_key:
            providers.append("volcengine")
        if self.tencent_secret_id and self.tencent_secret_key:
            providers.append("hunyuan")
        if self.sensenova_api_key:
            providers.append("sensenova")
        if self.skywork_api_key:
            providers.append("skywork")
        if self.siliconflow_api_key:
            providers.append("siliconflow")
            
        # Ollama is always available locally
        providers.append("ollama")
        
        return providers


# Global config instance
config = Config()
