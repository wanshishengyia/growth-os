import json
import logging
from datetime import datetime, timedelta
from backend.app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

VALID_INSIGHT_TYPES = ['observation', 'hypothesis', 'rule_of_thumb', 'mental_model', 'anti_pattern']


class InsightMinerAgent(BaseAgent):
    """A5: Mines actionable insights from logs and reviews."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_name = 'insight_miner'
        self.temperature = 0.3
        self.max_tokens = 2000

    def get_prompt_name(self) -> str:
        return self.prompt_name

    async def build_variables(self, input_data: dict) -> dict:
        days_back = input_data.get('days_back', 14)
        end_date = datetime.utcnow().strftime('%Y-%m-%d')
        start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        recent_logs = await self.db.get_daily_logs_range(start_date, end_date)
        reviews = await self.db.get_reviews_range(start_date, end_date)
        existing_insights = await self.db.get_insights()

        return {
            'start_date': start_date,
            'end_date': end_date,
            'recent_logs': json.dumps(recent_logs, indent=2) if recent_logs else '[]',
            'reviews': json.dumps(reviews, indent=2) if reviews else '[]',
            'existing_insights': json.dumps(existing_insights, indent=2) if existing_insights else '[]',
            'valid_types': ', '.join(VALID_INSIGHT_TYPES),
        }

    def parse_output(self, raw_output: str) -> dict:
        data = json.loads(raw_output)

        if 'insights' not in data or not isinstance(data['insights'], list):
            raise ValueError('Output must contain an "insights" list')

        for insight in data['insights']:
            required = ['text', 'type', 'confidence']
            for field in required:
                if field not in insight:
                    raise ValueError(f'Insight missing required field: {field}')

            # Validate type
            if insight['type'] not in VALID_INSIGHT_TYPES:
                raise ValueError(f'Invalid insight type: {insight["type"]}')

            # Validate confidence (0.0-1.0)
            insight['confidence'] = max(0.0, min(float(insight['confidence']), 1.0))

            # Enforce text length
            if len(insight['text']) > 300:
                insight['text'] = insight['text'][:300]

        return data

    def fallback(self) -> dict:
        return {
            'insights': [],
            'fallback': True,
            'message': 'Unable to mine insights. Keep logging consistently for better pattern detection.',
        }
