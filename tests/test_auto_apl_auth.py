"""test_auto_apl_auth.py -- issue #20.

auto_apl must not read, refresh or rewrite Claude Code's OAuth credentials
file. The only key source is ANTHROPIC_API_KEY (environment or .env).
"""
import sys, os, json, tempfile, inspect
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from apl import auto_apl


def _with_env(home, key, fn):
    saved = {k: os.environ.get(k) for k in ("HOME", "USERPROFILE", "ANTHROPIC_API_KEY")}
    os.environ["HOME"] = os.environ["USERPROFILE"] = str(home)
    os.environ.pop("ANTHROPIC_API_KEY", None)
    if key is not None:
        os.environ["ANTHROPIC_API_KEY"] = key
    try:
        return fn()
    finally:
        for k, v in saved.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)


def test_credentials_file_is_not_read_or_rewritten():
    repo_env = Path(auto_apl.__file__).parent.parent / ".env"
    if repo_env.exists():
        print("  (skipped: repo has a .env, so a key is legitimately found)")
        return
    with tempfile.TemporaryDirectory() as home:
        creds = Path(home) / ".claude" / ".credentials.json"
        creds.parent.mkdir()
        original = json.dumps({"claudeAiOauth": {"accessToken": "sk-ant-oat01-SECRET",
                                                 "expiresAt": 0, "refreshToken": "REFRESH"}})
        creds.write_text(original, encoding="utf-8")
        try:
            token = _with_env(home, None, auto_apl._get_api_token)
            raise AssertionError(f"expected RuntimeError, got a token: {token[:12]}")
        except RuntimeError as e:
            assert "ANTHROPIC_API_KEY" in str(e)
        assert creds.read_text(encoding="utf-8") == original, "credentials file was modified"


def test_env_key_is_used():
    with tempfile.TemporaryDirectory() as home:
        assert _with_env(home, "sk-ant-api03-abc", auto_apl._get_api_token) == "sk-ant-api03-abc"


def test_no_oauth_code_left():
    src = inspect.getsource(auto_apl)
    for banned in (".credentials.json", "oauth/token", "refreshToken", "_refresh_oauth_token"):
        assert banned not in src.replace("~/.claude/.credentials.json", ""), banned


def test_bearer_prefix_is_not_character_stripped():
    # 'Bearer '.lstrip chars would eat the leading 'ear' of this token
    assert auto_apl._auth_headers("Bearer earBraeX") == {"Authorization": "Bearer earBraeX"}
    assert auto_apl._auth_headers("sk-ant-oat01-x") == {"Authorization": "Bearer sk-ant-oat01-x"}
    assert auto_apl._auth_headers("sk-ant-api03-x") == {"x-api-key": "sk-ant-api03-x"}


if __name__ == "__main__":
    test_credentials_file_is_not_read_or_rewritten()
    test_env_key_is_used()
    test_no_oauth_code_left()
    test_bearer_prefix_is_not_character_stripped()
    print("test_auto_apl_auth: OK")
