import json
import os
from typing import Any, Dict

class Config:
    def __init__(self, config_path: str = "workflow.json"):
        self.config_path = config_path
        self._config_data = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found at {self.config_path}")
        
        with open(self.config_path, "r") as f:
            return json.load(f)

    @property
    def workflow_name(self) -> str:
        return self._config_data.get("workflow_name", "UnknownWorkflow")

    @property
    def match_threshold(self) -> float:
        return self._config_data.get("config", {}).get("match_threshold", 0.9)

    @property
    def two_way_tolerance_pct(self) -> float:
        return self._config_data.get("config", {}).get("two_way_tolerance_pct", 5)
    
    @property
    def checkpoint_table(self) -> str:
        return self._config_data.get("config", {}).get("checkpoint_table", "checkpoints")

    @property
    def default_db(self) -> str:
        return self._config_data.get("config", {}).get("default_db", "sqlite:///./demo.db")

    def get_stage_config(self, stage_id: str) -> Dict[str, Any]:
        stages = self._config_data.get("stages", [])
        for stage in stages:
            if stage["id"] == stage_id:
                return stage
        return {}

# Global config instance
settings = Config()
