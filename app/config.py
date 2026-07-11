"""環境変数ベースの設定。

秘密情報(APIキー等)は環境変数からのみ読み込み、コードにハードコードしない。
未設定の項目はNone/空文字となり、各サービスはその場合フォールバック動作を行う。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    value = os.environ.get(name, default)
    return value.strip() if value else value


@dataclass(frozen=True)
class AzureOpenAISettings:
    endpoint: str
    api_key: str
    deployment: str
    api_version: str

    @property
    def configured(self) -> bool:
        return bool(self.endpoint and self.api_key and self.deployment)


@dataclass(frozen=True)
class AzureSpeechSettings:
    key: str
    region: str
    stt_language: str
    tts_voice: str

    @property
    def configured(self) -> bool:
        return bool(self.key and self.region)


@dataclass(frozen=True)
class Settings:
    azure_openai: AzureOpenAISettings
    azure_speech: AzureSpeechSettings
    consultation_offices_path: Path
    voice_max_upload_bytes: int


_DEFAULT_VOICE_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB(数分程度の圧縮音声を想定)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_settings() -> Settings:
    """呼び出し時点の環境変数から設定を読み込む(テストで monkeypatch しやすいようにキャッシュしない)。"""
    azure_openai = AzureOpenAISettings(
        endpoint=_env("AZURE_OPENAI_ENDPOINT"),
        api_key=_env("AZURE_OPENAI_API_KEY"),
        deployment=_env("AZURE_OPENAI_DEPLOYMENT"),
        api_version=_env("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
    )
    azure_speech = AzureSpeechSettings(
        key=_env("AZURE_SPEECH_KEY"),
        region=_env("AZURE_SPEECH_REGION"),
        stt_language=_env("AZURE_SPEECH_STT_LANGUAGE", "ja-JP"),
        tts_voice=_env("AZURE_SPEECH_TTS_VOICE", "ja-JP-NanamiNeural"),
    )

    override_path = _env("CONSULTATION_OFFICES_PATH")
    if override_path:
        offices_path = Path(override_path)
    else:
        offices_path = _default_offices_path()

    voice_max_upload_bytes = _env_int(
        "VOICE_MAX_UPLOAD_BYTES", _DEFAULT_VOICE_MAX_UPLOAD_BYTES
    )

    return Settings(
        azure_openai=azure_openai,
        azure_speech=azure_speech,
        consultation_offices_path=offices_path,
        voice_max_upload_bytes=voice_max_upload_bytes,
    )


def _default_offices_path() -> Path:
    """リポジトリルートの data/consultation_offices.json を親ディレクトリを遡って探す。"""
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / "data" / "consultation_offices.json"
        if candidate.exists():
            return candidate
    # 見つからない場合は従来通りリポジトリルート想定のパスを返す(存在チェックは利用側で行う)
    return here.parents[1] / "data" / "consultation_offices.json"
