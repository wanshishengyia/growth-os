import json
import logging
from backend.app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class LoopCloserAgent(BaseAgent):
    """A2: Closes the daily loop by extracting assets and insights from raw notes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_name = 'loop_closer'
        self.temperature = 0.4
        self.max_tokens = 2000

    def get_prompt_name(self) -> str:
        return self.prompt_name

    async def build_variables(self, input_data: dict) -> dict:
        raw_notes = input_data.get('raw_notes', '')
        core_task = input_data.get('core_task', 'No task specified.')
        today = input_data.get('date', '')

        return {
            'raw_notes': raw_notes,
            'core_task': core_task,
            'today': today,
        }

    def parse_output(self, raw_output: str) -> dict:
        data = json.loads(raw_output)

        required = ['summary', 'mood', 'energy_level']
        for field in required:
            if field not in data:
                raise ValueError(f'Missing required field: {field}')

        # Validate mood
        valid_moods = ['great', 'good', 'neutral', 'low', 'bad']
        if data['mood'] not in valid_moods:
            data['mood'] = 'neutral'

        # Validate energy level
        data['energy_level'] = max(1, min(int(data['energy_level']), 10))

        # Ensure asset_candidates is a list
        if 'asset_candidates' not in data:
            data['asset_candidates'] = []
        for asset in data['asset_candidates']:
            if 'content' not in asset or 'type' not in asset:
                raise ValueError('Asset candidate missing content or type')

        # Ensure insight_candidates is a list
        if 'insight_candidates' not in data:
            data['insight_candidates'] = []
        for insight in data['insight_candidates']:
            if 'text' not in insight:
                raise ValueError('Insight candidate missing text')

        # Enforce summary length
        if len(data['summary']) > 500:
            data['summary'] = data['summary'][:500]

        return data

    def fallback(self) -> dict:
        return {
            'summary': 'Daily reflection completed.',
            'mood': 'neutral',
            'energy_level': 5,
            'asset_candidates': [],
            'insight_candidates': [],
            'fallback': True,
        }
