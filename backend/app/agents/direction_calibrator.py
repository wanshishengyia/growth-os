import json
import logging
from datetime import datetime, timedelta
from backend.app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

VALID_STAGES = ['exploring', 'building', 'scaling', 'optimizing', 'pivoting']


class DirectionCalibratorAgent(BaseAgent):
    """A7: Calibrates overall direction by evaluating goals, assets, and insights."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_name = 'direction_calibrator'
        self.temperature = 0.2
        self.max_tokens = 2000

    def get_prompt_name(self) -> str:
        return self.prompt_name

    async def build_variables(self, input_data: dict) -> dict:
        goals = await self.db.get_active_goals()
        asset_summary = await self.db.get_asset_summary()
        insight_summary = await self.db.get_insight_summary()

        # Completion stats (last 30 days)
        end_date = datetime.utcnow().strftime('%Y-%m-%d')
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
        logs = await self.db.get_daily_logs_range(start_date, end_date)
        completed = sum(1 for log in logs if log.get('core_task_completed'))
        total = len(logs)
        completion_rate = round(completed / max(total, 1) * 100)

        return {
            'goals': json.dumps(goals, indent=2) if goals else '[]',
            'asset_summary': json.dumps(asset_summary, indent=2) if asset_summary else '{}',
            'insight_summary': json.dumps(insight_summary, indent=2) if insight_summary else '{}',
            'completion_rate_30d': completion_rate,
            'completed_days': completed,
            'total_days': total,
            'valid_stages': ', '.join(VALID_STAGES),
            'date': end_date,
        }

    def parse_output(self, raw_output: str) -> dict:
        data = json.loads(raw_output)

        required = ['direction_alignment', 'stage_recommendation', 'goals_to_keep',
                     'goals_to_drop', 'goals_to_add', 'rationale']
        for field in required:
            if field not in data:
                raise ValueError(f'Missing required field: {field}')

        # Validate direction_alignment is 1-10
        data['direction_alignment'] = max(1, min(int(data['direction_alignment']), 10))

        # Validate stage_recommendation
        if data['stage_recommendation'] not in VALID_STAGES:
            raise ValueError(
                f'stage_recommendation must be one of {VALID_STAGES}, got: {data["stage_recommendation"]}'
            )

        # Validate lists
        for list_field in ['goals_to_keep', 'goals_to_drop', 'goals_to_add']:
            if not isinstance(data[list_field], list):
                data[list_field] = []

        # Enforce rationale length
        if len(data['rationale']) > 1000:
            data['rationale'] = data['rationale'][:1000]

        return data

    def fallback(self) -> dict:
        return {
            'direction_alignment': 5,
            'stage_recommendation': 'exploring',
            'goals_to_keep': [],
            'goals_to_drop': [],
            'goals_to_add': [],
            'rationale': 'Unable to perform direction calibration. Continue with current goals and review again next week.',
            'fallback': True,
        }
