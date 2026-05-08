import json
import logging
from datetime import datetime, timedelta
from backend.app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class ActionDeciderAgent(BaseAgent):
    """A1: Decides the single most important action for today."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_name = 'action_decider'
        self.temperature = 0.3
        self.max_tokens = 1500

    def get_prompt_name(self) -> str:
        return self.prompt_name

    async def build_variables(self, input_data: dict) -> dict:
        today = datetime.utcnow().strftime('%Y-%m-%d')
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')

        # Yesterday's log
        yesterday_log = await self.db.get_daily_log(yesterday)

        # Active goals
        active_goals = await self.db.get_active_goals()

        # Recent completion pattern (last 7 days)
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
        recent_logs = await self.db.get_daily_logs_range(seven_days_ago, today)
        completed_count = sum(1 for log in recent_logs if log.get('core_task_completed'))
        total_count = len(recent_logs)
        completion_rate = round(completed_count / max(total_count, 1) * 100)

        return {
            'today': today,
            'yesterday_log': json.dumps(yesterday_log) if yesterday_log else 'No log recorded yesterday.',
            'active_goals': json.dumps(active_goals, indent=2) if active_goals else 'No active goals set.',
            'completion_rate_7d': completion_rate,
            'completed_days': completed_count,
            'total_days': total_count,
        }

    def parse_output(self, raw_output: str) -> dict:
        data = json.loads(raw_output)

        required = ['core_task', 'reasoning', 'estimated_minutes']
        for field in required:
            if field not in data:
                raise ValueError(f'Missing required field: {field}')

        # Enforce length limits
        if len(data['core_task']) > 200:
            data['core_task'] = data['core_task'][:200]
        if len(data['reasoning']) > 500:
            data['reasoning'] = data['reasoning'][:500]

        data['estimated_minutes'] = max(5, min(int(data['estimated_minutes']), 480))

        return data

    def fallback(self) -> dict:
        return {
            'core_task': 'Review your goals and pick one small task to make progress on.',
            'reasoning': 'Unable to generate a personalized recommendation. Start by reviewing your active goals.',
            'estimated_minutes': 30,
            'fallback': True,
        }
