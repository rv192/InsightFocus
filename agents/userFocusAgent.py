import logging
from string import Template
from agents.baseAgent import PROMPTS, BaseAgent, ConfigError, IntelligentAPIError


class UserFocusAgent(BaseAgent):
    def __init__(self):
        super().__init__('FOCUS_MATCHER')

    async def judge_article_relevance(self, article, focus) -> bool:
        prompt_template = PROMPTS.get('judge_article_relevance')
        if not prompt_template:
            raise ConfigError("judge_article_relevance prompt not found")
        
        prompt = Template(prompt_template).safe_substitute(
            article_title=article['title'],
            article_summary=article['summary'],
            focus_content=focus
        )
        
        try:
            result = await self.call_ai_api(PROMPTS.get('judge_article_relevance_system', ""), prompt)

            isPass = result.get('is_relevant')
            reason = result.get('reason')
            logging.info(f"{isPass}：{reason}")

            return result.get('is_relevant', False)
        except IntelligentAPIError as e:
            logging.error(f"Article relevance judgment failed: {str(e)}")
            return False