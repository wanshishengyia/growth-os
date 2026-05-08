import json
import logging
from backend.app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

VALID_ASSET_TYPES = [
    'article', 'code_snippet', 'design', 'document', 'idea',
    'lesson_learned', 'note', 'process', 'template', 'tool', 'other'
]


class AssetClassifierAgent(BaseAgent):
    """A4: Classifies content into asset types aligned with goals."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_name = 'asset_classifier'
        self.temperature = 0.2
        self.max_tokens = 1000

    def get_prompt_name(self) -> str:
        return self.prompt_name

    async def build_variables(self, input_data: dict) -> dict:
        content = input_data.get('content', '')
        context = input_data.get('context', '')
        active_goals = await self.db.get_active_goals()

        return {
            'content': content,
            'context': context,
            'active_goals': json.dumps(active_goals, indent=2) if active_goals else 'No active goals.',
            'valid_types': ', '.join(VALID_ASSET_TYPES),
        }

    def parse_output(self, raw_output: str) -> dict:
        data = json.loads(raw_output)

        required = ['type', 'title', 'goal_alignment', 'tags', 'reusability_score']
        for field in required:
            if field not in data:
                raise ValueError(f'Missing required field: {field}')

        # Validate type is valid enum
        if data['type'] not in VALID_ASSET_TYPES:
            logger.warning(f'Invalid asset type: {data["type"]}, defaulting to "other"')
            data['type'] = 'other'

        # Validate reusability score
        data['reusability_score'] = max(1, min(int(data['reusability_score']), 10))

        # Validate tags
        if not isinstance(data['tags'], list):
            data['tags'] = []
        data['tags'] = [str(t).strip().lower() for t in data['tags'] if t][:10]

        # Enforce title length
        if len(data['title']) > 200:
            data['title'] = data['title'][:200]

        return data

    def fallback(self) -> dict:
        return {
            'type': 'other',
            'title': 'Unclassified Content',
            'goal_alignment': [],
            'tags': [],
            'reusability_score': 3,
            'fallback': True,
        }
