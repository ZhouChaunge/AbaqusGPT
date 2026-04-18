"""LLM client implementation using LiteLLM with multi-provider support."""

import os
from typing import Generator, Optional

import litellm

from ..config import config

# Model name mapping for LiteLLM
# LiteLLM uses specific prefixes for different providers
MODEL_MAPPING = {
    # OpenAI (2026 latest)
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt-4-turbo": "gpt-4-turbo",
    "o1": "o1",
    "o1-mini": "o1-mini",
    "o3-mini": "o3-mini",

    # Anthropic (Claude 4 series - 2026 latest)
    "claude-sonnet-4": "anthropic/claude-sonnet-4-20260401",
    "claude-opus-4": "anthropic/claude-opus-4-20260401",
    "claude-3.5-sonnet": "anthropic/claude-3-5-sonnet-20241022",
    "claude-3.5-haiku": "anthropic/claude-3-5-haiku-20241022",
    "claude-3-opus": "anthropic/claude-3-opus-20240229",

    # Google Gemini
    "gemini-2.0-flash": "gemini/gemini-2.0-flash",
    "gemini-1.5-pro": "gemini/gemini-1.5-pro",
    "gemini-1.5-flash": "gemini/gemini-1.5-flash",

    # 智谱 GLM (Zhipu) - 2026 latest
    "glm-4-plus": "zhipu/glm-4-plus",
    "glm-4": "zhipu/glm-4",
    "glm-4v-plus": "zhipu/glm-4v-plus",
    "glm-4-flash": "zhipu/glm-4-flash",

    # 通义千问 (Qwen / DashScope) - Qwen 2.5 series
    "qwen-max": "dashscope/qwen-max",
    "qwen-plus": "dashscope/qwen-plus",
    "qwen-turbo": "dashscope/qwen-turbo",
    "qwen2.5-72b": "dashscope/qwen2.5-72b-instruct",
    "qwen2.5-coder": "dashscope/qwen2.5-coder-32b-instruct",

    # DeepSeek - V3 and R1 series
    "deepseek-v3": "deepseek/deepseek-chat",
    "deepseek-r1": "deepseek/deepseek-reasoner",
    "deepseek-coder": "deepseek/deepseek-coder",

    # 百度文心 (ERNIE)
    "ernie-4.0": "qianfan/ernie-4.0-8k",
    "ernie-4.0-turbo": "qianfan/ernie-4.0-turbo-8k",

    # 月之暗面 Kimi (Moonshot)
    "kimi-latest": "moonshot/moonshot-v1-auto",
    "moonshot-v1-128k": "moonshot/moonshot-v1-128k",
    "moonshot-v1-32k": "moonshot/moonshot-v1-32k",

    # 零一万物 (Yi) - Yi-Lightning series
    "yi-lightning": "yi/yi-lightning",
    "yi-large": "yi/yi-large",
    "yi-medium": "yi/yi-medium",

    # 百川 (Baichuan)
    "baichuan4": "baichuan/Baichuan4",
    "baichuan3-turbo": "baichuan/Baichuan3-Turbo",

    # 阶跃星辰 (StepFun)
    "step-2": "stepfun/step-2-16k",
    "step-1-128k": "stepfun/step-1-128k",
    "step-1v": "stepfun/step-1v-32k",

    # MiniMax
    "abab7-chat": "minimax/abab7-chat",
    "abab6.5-chat": "minimax/abab6.5-chat",

    # 硅基流动 (SiliconFlow) - uses OpenAI-compatible API
    "siliconflow-deepseek-v3": "openai/deepseek-ai/DeepSeek-V3",
    "siliconflow-qwen": "openai/Qwen/Qwen2.5-72B-Instruct",

    # Ollama (local)
    "ollama-llama3.3": "ollama/llama3.3",
    "ollama-qwen2.5": "ollama/qwen2.5",
    "ollama-deepseek-r1": "ollama/deepseek-r1",
}


def _setup_api_keys():
    """Configure API keys for all providers in environment."""
    # OpenAI
    if config.openai_api_key:
        os.environ["OPENAI_API_KEY"] = config.openai_api_key
    if config.openai_api_base != "https://api.openai.com/v1":
        os.environ["OPENAI_API_BASE"] = config.openai_api_base

    # Anthropic
    if config.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = config.anthropic_api_key

    # 智谱 GLM
    if config.zhipu_api_key:
        os.environ["ZHIPUAI_API_KEY"] = config.zhipu_api_key

    # 通义千问 DashScope
    if config.dashscope_api_key:
        os.environ["DASHSCOPE_API_KEY"] = config.dashscope_api_key

    # DeepSeek
    if config.deepseek_api_key:
        os.environ["DEEPSEEK_API_KEY"] = config.deepseek_api_key

    # 百度 ERNIE
    if config.baidu_api_key:
        os.environ["QIANFAN_AK"] = config.baidu_api_key
    if config.baidu_secret_key:
        os.environ["QIANFAN_SK"] = config.baidu_secret_key

    # 月之暗面 Moonshot
    if config.moonshot_api_key:
        os.environ["MOONSHOT_API_KEY"] = config.moonshot_api_key

    # 零一万物 Yi
    if config.yi_api_key:
        os.environ["YI_API_KEY"] = config.yi_api_key

    # 百川 Baichuan
    if config.baichuan_api_key:
        os.environ["BAICHUAN_API_KEY"] = config.baichuan_api_key

    # 阶跃星辰 StepFun
    if config.stepfun_api_key:
        os.environ["STEPFUN_API_KEY"] = config.stepfun_api_key

    # MiniMax
    if config.minimax_api_key:
        os.environ["MINIMAX_API_KEY"] = config.minimax_api_key
    if config.minimax_group_id:
        os.environ["MINIMAX_GROUP_ID"] = config.minimax_group_id

    # 硅基流动 SiliconFlow (OpenAI-compatible)
    if config.siliconflow_api_key:
        os.environ["SILICONFLOW_API_KEY"] = config.siliconflow_api_key


class LLMClient:
    """Unified LLM client supporting multiple providers (15+ Chinese models)."""

    def __init__(self, model: Optional[str] = None):
        """
        Initialize LLM client.

        Args:
            model: Model name (e.g., 'gpt-4o', 'glm-4', 'qwen-max', 'deepseek-chat')
        """
        _setup_api_keys()

        raw_model = model or config.default_model
        self.model = MODEL_MAPPING.get(raw_model, raw_model)
        self.raw_model_name = raw_model

        # Configure LiteLLM settings
        litellm.drop_params = True  # Drop unsupported params for providers
        litellm.set_verbose = False

    @staticmethod
    def list_available_models() -> dict[str, list[str]]:
        """Return available models grouped by provider."""
        return {
            "OpenAI": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1", "o1-mini", "o3-mini"],
            "Anthropic": ["claude-sonnet-4", "claude-opus-4", "claude-3.5-sonnet", "claude-3.5-haiku", "claude-3-opus"],
            "Google Gemini": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
            "智谱 GLM": ["glm-4-plus", "glm-4", "glm-4v-plus", "glm-4-flash"],
            "通义千问 Qwen": ["qwen-max", "qwen-plus", "qwen-turbo", "qwen2.5-72b", "qwen2.5-coder"],
            "DeepSeek": ["deepseek-v3", "deepseek-r1", "deepseek-coder"],
            "百度文心 ERNIE": ["ernie-4.0", "ernie-4.0-turbo"],
            "月之暗面 Kimi": ["kimi-latest", "moonshot-v1-128k", "moonshot-v1-32k"],
            "零一万物 Yi": ["yi-lightning", "yi-large", "yi-medium"],
            "百川 Baichuan": ["baichuan4", "baichuan3-turbo"],
            "阶跃星辰 Step": ["step-2", "step-1-128k", "step-1v"],
            "MiniMax": ["abab7-chat", "abab6.5-chat"],
            "硅基流动 SiliconFlow": ["siliconflow-deepseek-v3", "siliconflow-qwen"],
            "Ollama (本地)": ["ollama-llama3.3", "ollama-qwen2.5", "ollama-deepseek-r1"],
        }

    def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 4096,
        history: Optional[list] = None,
    ) -> str:
        """
        Send a chat message and get a response.

        Args:
            message: User message
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum response tokens
            history: Conversation history as list of {role, content} dicts

        Returns:
            Assistant response text
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add conversation history
        if history:
            for msg in history:
                # Support both Pydantic models and plain dicts
                if hasattr(msg, 'role'):
                    role = msg.role
                    content = msg.content
                else:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": message})

        response = litellm.completion(
            model=self.model,
            messages=messages,
            temperature=temperature or config.temperature,
            max_tokens=max_tokens,
            timeout=config.timeout,
            num_retries=config.max_retries,
        )

        return response.choices[0].message.content

    def chat_stream(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        history: Optional[list] = None,
    ) -> Generator[str, None, None]:
        """
        Send a chat message and stream the response.

        Args:
            message: User message
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0-1)
            history: Conversation history as list of {role, content} dicts

        Yields:
            Response text chunks
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add conversation history
        if history:
            for msg in history:
                # Support both Pydantic models and plain dicts
                if hasattr(msg, 'role'):
                    role = msg.role
                    content = msg.content
                else:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": message})

        response = litellm.completion(
            model=self.model,
            messages=messages,
            temperature=temperature or config.temperature,
            stream=True,
            timeout=config.timeout,
        )

        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# Global client instance (lazy initialization)
_client: Optional[LLMClient] = None


def get_client(model: Optional[str] = None) -> LLMClient:
    """Get or create a global LLM client instance."""
    global _client
    if _client is None or (model and model != _client.raw_model_name):
        _client = LLMClient(model=model)
    return _client


def get_llm_client(model: Optional[str] = None) -> LLMClient:
    """
    Get or create the global LLM client.

    Args:
        model: Optional model override

    Returns:
        LLMClient instance
    """
    global _client

    if model:
        return LLMClient(model)

    if _client is None:
        _client = LLMClient()

    return _client
