import json
import logging
from datetime import datetime, timedelta
from backend.app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class PatternFinderAgent(BaseAgent):
    """A3: Finds patterns and trends across daily logs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_name = 'pattern_finder'
        self.temperature = 0.2
        self.max_tokens = 2000

    def get_prompt_name(self) -> str:
        return self.prompt_name

    async def build_variables(self, input_data: dict) -> dict:
        period_days = input_data.get('period_days', 14)
        end_date = input_data.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
        start_date = (
            datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=period_days)
        ).strftime('%Y-%m-%d')

        logs = await self.db.get_daily_logs_range(start_date, end_date)

        return {
            'period_days': period_days,
            'start_date': start_date,
            'end_date': end_date,
            'daily_logs': json.dumps(logs, indent=2) if logs else '[]',
            'log_count': len(logs),
        }

    def parse_output(self, raw_output: str) -> dict:
        data = json.loads(raw_output)

        required = ['patterns', 'trend', 'energy_trend', 'recommendation']
        for field in required:
            if field not in data:
                raise ValueError(f'Missing required field: {field}')

        # Validate trend
        valid_trends = ['rising', 'flat', 'falling']
        if data['trend'] not in valid_trends:
            raise ValueError(f'trend must be one of {valid_trends}, got: {data["trend"]}')
        if data['energy_trend'] not in valid_trends:
            raise ValueError(f'energy_trend must be one of {valid_trends}')

        # Validate patterns is a list
        if not isinstance(data['patterns'], list):
            raise ValueError('patterns must be a list')

        # Enforce limits
        if len(data['recommendation']) > 500:
            data['recommendation'] = data['recommendation'][:500]

        return data

    def fallback(self) -> dict:
        return {
            'patterns': [],
            'trend': 'flat',
            'energy_trend': 'flat',
            'recommendation': 'Not enough data to identify patterns. Keep logging daily for better insights.',
            'fallback': True,
        }
