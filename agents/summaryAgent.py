import logging
from string import Template
from agents.baseAgent import PROMPTS, IntelligentAPIError, BaseAgent, ConfigError
from conf.consts import GENRES, TOPICS


class SummaryAgent(BaseAgent):
    def __init__(self):
        super().__init__('CONTENT_PROCESSOR')

    async def process_content(self, title, content):
        prompt_template = PROMPTS.get('process_content')
        if not prompt_template:
            raise ConfigError("process_content prompt not found")
        
        prompt = Template(prompt_template).safe_substitute(title=title, content=content)
        
        try:
            result = await self.call_ai_api(PROMPTS.get('process_content_system', ""), prompt)
            return {
                'processed_content': result.get('processed_content', ''),
                'summary': result.get('summary', ''),
                'tags': result.get('tags', [])
            }
        except IntelligentAPIError as e:
            logging.error(f"Content processing failed: {str(e)}")
            return {'processed_content': '', 'summary': '', 'tags': []}

    async def classify_article(self, title, summary, tags):
        topics_info = "\n".join(f"{id}. {name}- {description}" for id, name, description in TOPICS)
        genres_info = "\n".join(f"{id}. {name} - {description}" for id, name, description in GENRES)

        prompt = Template(PROMPTS['classify_article']).safe_substitute(
            topics_info=topics_info, genres_info=genres_info, title=title, summary=summary, tags=', '.join(tags)
        )
        
        try:
            result = await self.call_ai_api(PROMPTS['classify_article_system'], prompt)
            return {
                'topic_id': result.get('topic_id'),
                'genre_id': result.get('genre_id')
            }
        except IntelligentAPIError as e:
            logging.error(f"Article genre and topic identification failed: {str(e)}")
            return {'topic_id': None, 'genre_id': None}