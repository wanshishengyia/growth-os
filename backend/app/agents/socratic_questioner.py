import json
import logging
from datetime import datetime, timedelta
from backend.app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

VALID_ANGLES = [
    'assumption_challenge', 'alternative_framing', 'root_cause',
    'counterfactual', 'first_principles', 'contrarian', 'scaling_question'
]


class SocraticQuestionerAgent(BaseAgent):
    """A6: Generates Socratic questions to deepen self-reflection in reviews."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_name = 'socratic_questioner'
        self.temperature = 0.5
        self.max_tokens = 1500

    def get_prompt_name(self) -> str:
        return self.prompt_name

    async def build_variables(self, input_data: dict) -> dict:
        days_back = input_data.get('period_days', 7)
        end_date = input_data.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
        start_date = (
            datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=days_back)
        ).strftime('%Y-%m-%d')

        logs = await self.db.get_daily_logs_range(start_date, end_date)
        goals = await self.db.get_active_goals()
        recent_insights = await self.db.get_insights(limit=5)

        return {
            'start_date': start_date,
            'end_date': end_date,
            'period_days': days_back,
            'daily_logs': json.dumps(logs, indent=2) if logs else '[]',
            'active_goals': json.dumps(goals, indent=2) if goals else '[]',
            'recent_insights': json.dumps(recent_insights, indent=2) if recent_insights else '[]',
            'valid_angles': ', '.join(VALID_ANGLES),
        }

    def parse_output(self, raw_output: str) -> dict:
        data = json.loads(raw_output)

        if 'questions' not in data or not isinstance(data['questions'], list):
            raise ValueError('Output must contain a "questions" list')

        for q in data['questions']:
            required = ['question', 'angle', 'depth_level']
            for field in required:
                if field not in q:
                    raise ValueError(f'Question missing required field: {field}')

            # Validate angle
            if q['angle'] not in VALID_ANGLES:
                logger.warning(f'Invalid angle: {q["angle"]}, defaulting to assumption_challenge')
                q['angle'] = 'assumption_challenge'

            # Validate depth level (1-3)
            q['depth_level'] = max(1, min(int(q['depth_level']), 3))

            # Enforce question length
            if len(q['question']) > 300:
                q['question'] = q['question'][:300]

        return data

    def fallback(self) -> dict:
        return {
            'questions': [
                {
                    'question': 'What assumption am I making that might not be true?',
                    'angle': 'assumption_challenge',
                    'depth_level': 1,
                },
                {
                    'question': 'If I had to achieve the same goal with half the resources, what would I do differently?',
                    'angle': 'first_principles',
                    'depth_level': 2,
                },
            ],
            'fallback': True,
        }
