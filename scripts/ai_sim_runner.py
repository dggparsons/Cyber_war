#!/usr/bin/env python3
"""
Simple AI simulation harness for Cyber War Room.

This script logs in as the GM and a roster of teams, plays several rounds using
rule-based agents, and exports a summary JSON file suitable for the reveal view.

Usage:
    python scripts/ai_sim_runner.py --config ai_sim_config.json --output results/run.json
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from openai import OpenAI, AzureOpenAI


def _log(message: str):
    print(f"[sim] {message}", flush=True)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _save_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


@dataclass
class TeamConfig:
    display_name: str
    join_code: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None


@dataclass
class RunnerConfig:
    base_url: str
    gm_email: str
    gm_password: str
    teams: List[TeamConfig]
    rounds: int = 6
    intel_success_chance: float = 0.2
    vote_positive_bias: float = 0.55

    @staticmethod
    def from_dict(payload: dict) -> "RunnerConfig":
        teams = [TeamConfig(**item) for item in payload.get("teams", [])]
        return RunnerConfig(
            base_url=payload["base_url"].rstrip("/"),
            gm_email=payload["gm_email"],
            gm_password=payload["gm_password"],
            teams=teams,
            rounds=payload.get("rounds", 6),
            intel_success_chance=payload.get("intel_success_chance", 0.2),
            vote_positive_bias=payload.get("vote_positive_bias", 0.55),
        )

    @staticmethod
    def from_env(env: dict) -> "RunnerConfig":
        try:
            base_url = env["SIM_BASE_URL"].rstrip("/")
            gm_email = env["SIM_GM_EMAIL"]
            gm_password = env["SIM_GM_PASSWORD"]
        except KeyError as exc:
            raise RuntimeError(f"Missing required environment variable: {exc}") from exc
        rounds = int(env.get("SIM_ROUNDS", 6))
        intel = float(env.get("SIM_INTEL_SUCCESS", 0.2))
        vote_bias = float(env.get("SIM_VOTE_BIAS", 0.55))
        join_codes = [code.strip() for code in env.get("SIM_TEAM_JOIN_CODES", "").split(",") if code.strip()]
        teams = []
        for index, code in enumerate(join_codes):
            teams.append(
                TeamConfig(
                    display_name=f"SIM-{code.replace('-', '')}",
                    join_code=code,
                )
            )
        if not teams:
            raise RuntimeError("No team join codes provided (SIM_TEAM_JOIN_CODES).")
        return RunnerConfig(
            base_url=base_url,
            gm_email=gm_email,
            gm_password=gm_password,
            teams=teams,
            rounds=rounds,
            intel_success_chance=intel,
            vote_positive_bias=vote_bias,
        )


class APISession:
    def __init__(self, base_url: str):
        self.session = requests.Session()
        self.base_url = base_url.rstrip("/")

    def get(self, path: str) -> requests.Response:
        resp = self.session.get(f"{self.base_url}{path}", timeout=20)
        resp.raise_for_status()
        return resp

    def post(self, path: str, json_payload: Optional[dict] = None) -> requests.Response:
        resp = self.session.post(f"{self.base_url}{path}", json=json_payload, timeout=20)
        resp.raise_for_status()
        return resp


class Agent:
    def __init__(
        self,
        config: TeamConfig,
        base_url: str,
        vote_bias: float,
        intel_chance: float,
        llm_client: Optional[OpenAI],
        llm_model: Optional[str],
    ):
        self.config = config
        self.api = APISession(base_url)
        self.vote_bias = vote_bias
        self.intel_chance = intel_chance
        self.team_id: Optional[int] = None
        self.llm = llm_client
        self.llm_model = llm_model

    def join_or_login(self):
        if self.config.email and self.config.password:
            self._login(self.config.email, self.config.password)
            return
        if not self.config.join_code:
            raise ValueError("Join code required when email/password not provided.")
        payload = {
            "display_name": self.config.display_name,
            "join_code": self.config.join_code,
        }
        data = self.api.post("/api/auth/join", json_payload=payload).json()
        self.config.email = data["user"]["email"]
        self.config.password = data["password"]
        _log(f"{self.config.display_name} joined as {self.config.email}")

    def _login(self, email: str, password: str):
        resp = self.api.post("/api/auth/login", json_payload={"email": email, "password": password})
        data = resp.json()
        self.team_id = data["user"]["team_id"]
        _log(f"{self.config.display_name} logged in (team_id={self.team_id})")

    def ensure_logged_in(self):
        if not self.config.email or not self.config.password:
            raise ValueError("Agent missing credentials.")
        self._login(self.config.email, self.config.password)

    def fetch_state(self) -> dict:
        resp = self.api.get("/api/game/state")
        state = resp.json()
        self.team_id = state["team"]["id"]
        return state

    def choose_actions(self, state: dict, action_catalog: List[dict], targets: List[int]) -> Dict[int, dict]:
        proposals = {item["slot"]: item for item in state.get("proposals", [])}
        choices: Dict[int, dict] = {}
        slots = [1, 2, 3]
        for slot in slots:
            if slot in proposals and proposals[slot]["status"] == "locked":
                continue
            action = self._select_action(action_catalog, nuke_unlocked=state["global"].get("nuke_unlocked", False))
            target_id = None
            if action["target_required"] and targets:
                target_id = random.choice([tid for tid in targets if tid != self.team_id])
            choices[slot] = {"action_code": action["code"], "target_team_id": target_id}
        return choices

    def _select_action(self, catalog: List[dict], nuke_unlocked: bool) -> dict:
        if self.llm and self.llm_model:
            available = [item for item in catalog if nuke_unlocked or item["category"] != "nuclear"]
            prompt = (
                f"You are commander of {self.config.display_name}. Choose one action code from this list:\n"
                + "\n".join(f"- {item['code']} ({item['category']}): {item['description']}" for item in available)
                + "\nRespond with only the action code."
            )
            try:
                response = self.llm.chat.completions.create(
                    model=self.llm_model,
                    temperature=0.3,
                    messages=[
                        {"role": "system", "content": [{"type": "text", "text": "You pick one action code per request."}]},
                        {"role": "user", "content": [{"type": "text", "text": prompt}]},
                    ],
                )
                text = response.choices[0].message.content.strip().upper()
                match = next((item for item in available if item["code"] == text), None)
                if match:
                    return match
            except Exception as exc:
                _log(f"{self.config.display_name} LLM selection failed: {exc}")
        priorities = ["non_violent", "posturing", "status_quo", "de_escalation", "violent", "nuclear"]
        filtered = [action for action in catalog if nuke_unlocked or action["category"] != "nuclear"]
        filtered.sort(key=lambda item: priorities.index(item["category"]) if item["category"] in priorities else 99)
        return random.choice(filtered[:8] or filtered)

    def submit_choices(self, choices: Dict[int, dict]):
        for slot, payload in choices.items():
            body = {"slot": slot, "action_code": payload["action_code"], "target_team_id": payload["target_team_id"]}
            try:
                self.api.post("/api/game/proposals", json_payload=body)
            except requests.HTTPError as exc:
                _log(f"{self.config.display_name}: failed to submit slot {slot}: {exc}")

    def cast_votes(self, state: dict):
        for proposal in state.get("proposals", []):
            vote_value = 1 if random.random() < self.vote_bias else -1
            try:
                self.api.post("/api/game/votes", json_payload={"proposal_id": proposal["id"], "value": vote_value})
            except requests.HTTPError:
                continue

    def attempt_intel(self, state: dict):
        for intel in state.get("intel_drops", []):
            if intel["status"] == "solved":
                continue
            if random.random() > self.intel_chance:
                continue
            # We don't know the actual solution; this is a placeholder request to keep flow realistic.
            fake_answer = f"guess-{random.randint(1000,9999)}"
            try:
                self.api.post("/api/game/intel/solve", json_payload={"intel_id": intel["id"], "answer": fake_answer})
            except requests.HTTPError:
                pass

    def play_round(self, action_catalog: List[dict], leaderboard: dict):
        state = self.fetch_state()
        targets = [entry["team_id"] for entry in leaderboard.get("entries", [])]
        choices = self.choose_actions(state, action_catalog, targets)
        self.submit_choices(choices)
        self.cast_votes(state)
        self.attempt_intel(state)


def build_llm_client() -> Optional[OpenAI]:
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        _log("No OpenAI API key provided; falling back to heuristic agents.")
        return None
    if endpoint and deployment:
        _log(f"Using Azure OpenAI deployment {deployment} at {endpoint}")
        return AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=os.environ.get("AZURE_API_VERSION", "2024-05-01-preview"),
        )
    return OpenAI(api_key=api_key)


class GameMaster:
    def __init__(self, config: RunnerConfig):
        self.api = APISession(config.base_url)
        self.config = config
        self.logged_in = False

    def login(self):
        if self.logged_in:
            return
        self.api.post("/api/auth/login", json_payload={"email": self.config.gm_email, "password": self.config.gm_password})
        self.logged_in = True
        _log("GM logged in.")

    def start_round(self):
        self.api.post("/api/admin/rounds/start")

    def advance_round(self):
        self.api.post("/api/admin/rounds/advance")

    def get_leaderboard(self) -> dict:
        resp = self.api.get("/api/game/leaderboard")
        return resp.json()

    def get_action_catalog(self) -> List[dict]:
        resp = self.api.get("/api/game/actions")
        return resp.json()


class SimulationRunner:
    def __init__(self, config: RunnerConfig):
        self.config = config
        self.gm = GameMaster(config)
        llm_client = build_llm_client()
        llm_model = os.environ.get("LLM_MODEL") or os.environ.get("AZURE_OPENAI_DEPLOYMENT")
        self.agents = [
            Agent(team_cfg, config.base_url, config.vote_positive_bias, config.intel_success_chance, llm_client, llm_model)
            for team_cfg in config.teams
        ]
        self.action_catalog: List[dict] = []
        self.results: List[dict] = []

    def bootstrap(self):
        self.gm.login()
        self.action_catalog = self.gm.get_action_catalog()
        for agent in self.agents:
            agent.join_or_login()
            agent.ensure_logged_in()

    def run(self):
        self.bootstrap()
        for round_num in range(1, self.config.rounds + 1):
            _log(f"=== Round {round_num} ===")
            self.gm.start_round()
            leaderboard = self.gm.get_leaderboard()
            for agent in self.agents:
                agent.play_round(self.action_catalog, leaderboard)
            time.sleep(1.0)
            self.gm.advance_round()
            round_summary = self.gm.get_leaderboard()
            self.results.append({"round": round_num, "leaderboard": round_summary})
            time.sleep(1.0)

    def export_results(self, path: Path):
        payload = {
            "meta": {
                "rounds": self.config.rounds,
                "timestamp": int(time.time()),
            },
            "rounds": self.results,
        }
        _save_json(path, payload)
        _log(f"Saved simulation log to {path}")


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run automated AI simulation for Cyber War Room.")
    parser.add_argument("--config", help="Path to JSON config file with credentials and roster.")
    parser.add_argument("--output", required=True, help="Path to write results JSON.")
    parser.add_argument("--env-openai", default=".env.openai", help="Path to .env file with OpenAI/Azure keys (optional).")
    parser.add_argument("--env-sim", default=".env.ai_sim", help="Path to .env file with simulation credentials (optional).")
    return parser.parse_args(argv)


def main(argv: List[str]):
    args = parse_args(argv)
    for env_path in (Path(args.env_openai), Path(args.env_sim)):
        if env_path.exists():
            load_dotenv(env_path)
    env_vars = os.environ
    cfg: RunnerConfig
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            cfg = RunnerConfig.from_dict(_load_json(config_path))
        else:
            _log(f"Config file {config_path} not found; falling back to environment variables.")
            cfg = RunnerConfig.from_env(env_vars)
    else:
        cfg = RunnerConfig.from_env(env_vars)
    runner = SimulationRunner(cfg)
    runner.run()
    runner.export_results(Path(args.output))


if __name__ == "__main__":
    main(sys.argv[1:])
