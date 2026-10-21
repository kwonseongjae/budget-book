import pytest

import auth


def test_client_secret_env_missing(monkeypatch):
    monkeypatch.delenv("BUDGET_CLIENT_SECRET", raising=False)
    with pytest.raises(ValueError, match="BUDGET_CLIENT_SECRET not set"):
        auth.client_secret_path()


def test_client_secret_file_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("BUDGET_CLIENT_SECRET", str(tmp_path / "nope.json"))
    with pytest.raises(ValueError, match="client_secret 파일 없음"):
        auth.client_secret_path()


def test_scopes_cover_sheets_drive_script():
    assert set(auth.SCOPES) == {
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/script.projects",
    }


def test_token_lives_outside_windows_drive_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("BUDGET_TOKEN_FILE", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert auth.token_path() == tmp_path / ".config" / "budget-book" / "token.json"
    monkeypatch.setenv("BUDGET_TOKEN_FILE", str(tmp_path / "x.json"))
    assert auth.token_path() == tmp_path / "x.json"


def test_legacy_token_moved_with_owner_only_permissions(monkeypatch, tmp_path):
    legacy = tmp_path / "old" / "token.json"
    legacy.parent.mkdir()
    legacy.write_text('{"t": 1}')
    new = tmp_path / "cfg" / "budget-book" / "token.json"
    monkeypatch.setattr(auth, "LEGACY_TOKEN", legacy)
    monkeypatch.setenv("BUDGET_TOKEN_FILE", str(new))
    assert auth.migrate_legacy_token() == new
    assert new.read_text() == '{"t": 1}' and not legacy.exists()
    assert new.stat().st_mode & 0o777 == 0o600 and new.parent.stat().st_mode & 0o777 == 0o700
    assert auth.migrate_legacy_token() == new  # 두 번째는 아무 일 없음
