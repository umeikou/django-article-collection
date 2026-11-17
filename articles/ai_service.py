"""
AI服务 - DeepSeek 集成
用于文章内容分析和摘要生成
"""

import os
import json
import logging
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_TIMEOUT = 30


class DeepSeekAIService:
    """DeepSeek AI 服务（OpenAI 兼容接口）"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY', '')
        self.model = model or os.getenv('DEEPSEEK_MODEL', DEFAULT_MODEL)
        self.base_url = (base_url or os.getenv('DEEPSEEK_BASE_URL', DEFAULT_BASE_URL)).rstrip('/')
        try:
            self.timeout = int(timeout or os.getenv('DEEPSEEK_TIMEOUT', DEFAULT_TIMEOUT))
        except (TypeError, ValueError):
            self.timeout = DEFAULT_TIMEOUT

        if not self.api_key:
            logger.warning("未设置 DEEPSEEK_API_KEY，AI 功能将不可用")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.5,
        top_p: float = 0.9,
    ) -> str:
        """
        通用文本生成。调用 DeepSeek chat/completions 接口。
        返回模型输出文本；失败返回空字符串（并记录日志）。

        注意：deepseek-v4-flash 等推理模型会先产生 reasoning_content（思维链），
        再输出 message.content。max_tokens 需要同时覆盖两者，所以默认放到 2048。
        """
        if not self.is_available():
            logger.warning("AI 服务不可用，跳过生成")
            return ""

        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": False,
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            if resp.status_code != 200:
                logger.error(f"DeepSeek API 请求失败: status={resp.status_code} body={resp.text[:500]}")
                return ""
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                logger.error(f"DeepSeek API 返回无 choices: {data}")
                return ""
            choice = choices[0]
            message = choice.get("message") or {}
            content = (message.get("content") or "").strip()
            if not content:
                finish = choice.get("finish_reason")
                reasoning_len = len(message.get("reasoning_content") or "")
                logger.error(
                    f"DeepSeek 返回 content 为空（finish_reason={finish}, reasoning_len={reasoning_len}），"
                    f"通常意味着 max_tokens 被推理过程耗尽，请加大 max_tokens"
                )
                return ""
            return content
        except requests.RequestException as e:
            logger.error(f"调用 DeepSeek API 网络异常: {e}")
            return ""
        except ValueError as e:
            logger.error(f"DeepSeek API 响应解析失败: {e}")
            return ""

    def analyze_article(self, content: str, title: str = "") -> Dict[str, str]:
        """
        分析文章内容，提取核心观点和生成摘要。
        返回 {'key_point': ..., 'summary': ...}
        """
        if not self.is_available():
            logger.warning("AI 服务不可用，跳过分析")
            return {'key_point': '', 'summary': ''}

        if not content or len(content.strip()) < 50:
            logger.warning("文章内容过短，跳过 AI 分析")
            return {'key_point': '', 'summary': ''}

        # 不截断内容：全文送入分析（依赖模型长上下文；超长导致的 API 异常由下方兜底）
        try:
            key_point = self._extract_key_point(content, title)
            summary = self._generate_summary(content, title)
            return {'key_point': key_point, 'summary': summary}
        except Exception as e:
            logger.error(f"AI 分析失败: {e}")
            return {'key_point': '', 'summary': ''}

    def _extract_key_point(self, content: str, title: str = "") -> str:
        prompt = f"""请阅读以下文章，提炼出其中"值得思考"的主要观点，并以结构化方式输出。

文章标题：{title if title else '无'}

文章内容：
{content}

请遵循以下要求：

【内容要求】
- 提炼让读者读完会停下来想一想的观点，而不是流水账式的概括
- 优先选择有冲击力、反常识、可被引用的金句式表达
- 不要重复，不要凑数；2~5 条最佳，宁少勿滥
- 用陈述句，不要疑问句、不要"我们应该……"这类口号

【文字风格】
- 简洁、直白、口语化，像跟朋友讲话
- 拒绝抽象大词：不要"底层逻辑/赋能/抓手/范式/生态"等空话
- 每条不超过 60 字；如能压到 30 字以内更好
- 必要时可保留原文中的金句，但要去掉冗余修饰

【输出格式】（严格按此结构，不要任何额外说明）
1. 主要观点
1.1 [第一条观点]
1.2 [第二条观点]
1.3 [第三条观点]
……

输出："""

        text = self.generate(prompt, max_tokens=2048, temperature=0.4, top_p=0.9)
        if not text:
            return ""
        # 清理可能的引号和多余空白
        text = text.strip().strip('"\'""''')
        return text[:500]

    def _generate_summary(self, content: str, title: str = "") -> str:
        prompt = f"""请阅读以下文章，生成一个300字左右的摘要。

文章标题：{title if title else '无'}

文章内容：
{content}

要求：
1. 摘要长度控制在280-320字之间
2. 准确概括文章的主要内容和关键信息
3. 保持客观中立的语气
4. 结构清晰，逻辑连贯
5. 只输出摘要内容，不要有其他说明文字

摘要："""

        text = self.generate(prompt, max_tokens=2048, temperature=0.5, top_p=0.9)
        return text[:500] if text else ""

    def batch_analyze(self, articles: list) -> list:
        results = []
        for article in articles:
            results.append(self.analyze_article(
                content=article.get('content', ''),
                title=article.get('title', ''),
            ))
        return results


class PodcastAnalysisClient:
    """Bounded JSON-only client used by the durable podcast pipeline."""
    def __init__(self):
        from django.conf import settings
        self.api_key = os.getenv('DEEPSEEK_API_KEY', '')
        self.model = os.getenv('DEEPSEEK_MODEL', DEFAULT_MODEL)
        self.base_url = os.getenv('DEEPSEEK_BASE_URL', DEFAULT_BASE_URL).rstrip('/')
        self.limit = getattr(settings, 'PODCAST_AI_INPUT_MAX', 2800)

    def generate_or_raise(self, kind, title, text):
        if kind not in {'chunk', 'rollup'} or not isinstance(text, str) or not text.strip() or len(text) > self.limit:
            raise RuntimeError('analysis_input_invalid')
        if not self.api_key:
            raise RuntimeError('analysis_credentials_missing')
        prompt = (
            '请分析以下内容并只返回 JSON，格式为 {"summary":"...","key_points":["..."]}。\n'
            '\n【内容要求】\n'
            '- 提炼让读者读完会停下来想一想的观点，而不是流水账式的概括\n'
            '- 优先选择有冲击力、反常识、可被引用的金句式表达\n'
            '- 不要重复，不要凑数；key_points 2~5 条最佳，宁少勿滥\n'
            '- 用陈述句，不要疑问句、不要"我们应该……"这类口号\n'
            '\n【文字风格】\n'
            '- 简洁、直白、口语化，像跟朋友讲话\n'
            '- 拒绝抽象大词：不要"底层逻辑/赋能/抓手/范式/生态"等空话\n'
            '- 每条要点不超过 60 字；必要时可保留原文金句，但去掉冗余修饰\n'
            '\n【summary 要求】\n'
            '- 300 字左右的客观摘要，概括本期主要内容与关键信息，结构清晰、逻辑连贯\n'
            '\n标题：' + title + '\n内容：' + text)
        try:
            response = requests.post(self.base_url + '/v1/chat/completions', headers={
                'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
                json={'model': self.model, 'messages': [{'role': 'user', 'content': prompt}], 'stream': False}, timeout=30)
        except requests.RequestException:
            raise RuntimeError('analysis_uncertain')
        if response.status_code in {400, 401, 403}:
            raise RuntimeError('analysis_configuration_error')
        if response.status_code == 429:
            raise RuntimeError('analysis_rate_limited')
        if response.status_code != 200:
            raise RuntimeError('analysis_uncertain')
        try:
            text_result = response.json()['choices'][0]['message']['content']
            data = json.loads(text_result)
        except (ValueError, KeyError, IndexError, TypeError):
            raise RuntimeError('analysis_uncertain')
        summary, points = data.get('summary'), data.get('key_points')
        if not isinstance(summary, str) or not summary.strip() or not isinstance(points, list):
            raise RuntimeError('analysis_result_invalid')
        points = [p.strip() for p in points if isinstance(p, str) and p.strip()]
        if len(points) < 2:
            raise RuntimeError('analysis_result_invalid')
        # Normalize to storage bounds instead of rejecting verbose-but-valid
        # content: LLMs occasionally return 6+ points or overlong sentences.
        return {'summary': summary.strip()[:500], 'key_points': [p[:80] for p in points[:5]]}


# 兼容旧引用：保留 QwenAIService 名称作为别名，避免外部 import 报错
QwenAIService = DeepSeekAIService

# 全局实例
ai_service = DeepSeekAIService()


def get_ai_service() -> DeepSeekAIService:
    return ai_service
