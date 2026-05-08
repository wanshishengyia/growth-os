import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Any
from backend.app.services.llm_client import LLMClient
from backend.app.services.prompt_loader import PromptLoader
from backend.app.services.db_service import DBService

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    def __init__(self, llm: LLMClient, prompt_loader: PromptLoader, db: DBService):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.db = db
        self.agent_name = self.__class__.__name__
        self.prompt_version = 'v1.0'
        self.temperature = 0.3
        self.max_tokens = 2000

    @abstractmethod
    def get_prompt_name(self) -> str:
        pass

    @abstractmethod
    async def build_variables(self, input_data: dict) -> dict:
        pass

    @abstractmethod
    def parse_output(self, raw_output: str) -> dict:
        pass

    async def run(self, input_data: dict) -> dict:
        start_time = time.time()
        try:
            variables = await self.build_variables(input_data)
            rendered = self.prompt_loader.render(
                self.get_prompt_name(), self.prompt_version, variables
            )
            messages = [{'role': 'user', 'content': rendered}]
            result = await self.llm.chat_json(
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            latency_ms = int((time.time() - start_time) * 1000)
            parsed = self.parse_output(result['content'])
            await self.db.log_interaction(
                agent_name=self.agent_name,
                prompt_version=self.prompt_version,
                input_data=input_data,
                output_data=parsed,
                model=result['model'],
                input_tokens=result['input_tokens'],
                output_tokens=result['output_tokens'],
                cost_usd=self._estimate_cost(result),
                latency_ms=latency_ms,
                status='success'
            )
            return parsed
        except Exception as e:
            logger.error(f'{self.agent_name} failed: {e}')
            await self.db.log_interaction(
                agent_name=self.agent_name,
                prompt_version=self.prompt_version,
                input_data=input_data,
                output_data=None,
                model=None,
                input_tokens=0,
                output_tokens=0,
                cost_usd=0,
                latency_ms=int((time.time() - start_time) * 1000),
                status='error',
                error_message=str(e)
            )
            raise

    def _estimate_cost(self, result: dict) -> float:
        input_cost = result['input_tokens'] * 3.0 / 1_000_000
        output_cost = result['output_tokens'] * 15.0 / 1_000_000
        return round(input_cost + output_cost, 6)
