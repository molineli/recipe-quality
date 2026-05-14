from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from typing import Any


class FatSecretError(RuntimeError):
    """Raised when FatSecret cannot complete a request."""


@dataclass(slots=True)
class FatSecretConfig:
    client_id: str
    client_secret: str
    scope: str = "basic"
    region: str | None = "US"
    language: str | None = "en"
    token_url: str = "https://oauth.fatsecret.com/connect/token"
    api_url: str = "https://platform.fatsecret.com/rest/server.api"
    timeout_seconds: float = 20.0

    @classmethod
    def from_env(cls) -> "FatSecretConfig":
        """从环境变量或 .env 文件读取 FatSecret 配置。"""
        try:
            from dotenv import load_dotenv
        except ModuleNotFoundError:
            load_dotenv = None
        if load_dotenv:
            load_dotenv()
        client_id = os.getenv("FATSECRET_CLIENT_ID")
        client_secret = os.getenv("FATSECRET_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise FatSecretError(
                "Missing FATSECRET_CLIENT_ID or FATSECRET_CLIENT_SECRET in environment."
            )
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            scope=os.getenv("FATSECRET_SCOPE", "basic"),
            region=os.getenv("FATSECRET_REGION") or None,
            language=os.getenv("FATSECRET_LANGUAGE") or None,
        )


class FatSecretClient:
    def __init__(self, config: FatSecretConfig | None = None, session: Any | None = None):
        """初始化 FatSecret 客户端，可注入 session 以便测试。"""
        self.config = config or FatSecretConfig.from_env()
        if session is None:
            try:
                import requests
            except ModuleNotFoundError as exc:
                raise FatSecretError(
                    "The 'requests' package is required for FatSecret API calls. "
                    "Install dependencies with: python -m pip install -e ."
                ) from exc
            session = requests.Session()
            session.trust_env = False
        self.session = session
        self._access_token: str | None = None
        self._token_expires_at = 0.0

    def get_access_token(self) -> str:
        """获取并缓存 FatSecret OAuth2 access token。"""
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token

        credentials = f"{self.config.client_id}:{self.config.client_secret}".encode("utf-8")
        auth_header = base64.b64encode(credentials).decode("ascii")
        response = self.session.post(
            self.config.token_url,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials", "scope": self.config.scope},
            timeout=self.config.timeout_seconds,
        )
        self._raise_for_response(response, "FatSecret token request failed")
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise FatSecretError("FatSecret token response did not include access_token.")
        self._access_token = token
        self._token_expires_at = time.time() + int(payload.get("expires_in", 86400))
        return token

    def search_foods(self, query: str, max_results: int = 10) -> dict[str, Any]:
        """调用 foods.search.v5 通过自然语言搜索食物。"""
        params: dict[str, Any] = {
            "method": "foods.search.v5",
            "format": "json",
            "search_expression": query,
            "max_results": max_results,
        }
        self._add_localization(params)
        return self._get(params)

    def get_food(self, food_id: str) -> dict[str, Any]:
        """调用 food.get.v5 获取指定id食物详情。"""
        params: dict[str, Any] = {
            "method": "food.get.v5",
            "format": "json",
            "food_id": food_id,
        }
        self._add_localization(params)
        return self._get(params)

    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        """向 FatSecret REST API 发送 GET 请求并处理错误响应。"""
        response = self.session.get(
            self.config.api_url,
            headers={"Authorization": f"Bearer {self.get_access_token()}"},
            params=params,
            timeout=self.config.timeout_seconds,
        )
        self._raise_for_response(response, "FatSecret API request failed")
        payload = response.json()
        error = payload.get("error")
        if error:
            raise FatSecretError(f"FatSecret API error: {error}")
        return payload

    def _add_localization(self, params: dict[str, Any]) -> None:
        """按配置向请求参数追加 region/language 本地化选项。"""
        if self.config.region:
            params["region"] = self.config.region
        if self.config.language:
            params["language"] = self.config.language

    @staticmethod
    def _raise_for_response(response: Any, message: str) -> None:
        """将 HTTP 错误响应转换为 FatSecretError。"""
        if response.status_code >= 400:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise FatSecretError(f"{message}: HTTP {response.status_code} {detail}")
