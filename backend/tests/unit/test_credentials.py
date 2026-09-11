"""Unit tests for host/player credentials (MASTER_SPEC.md §8, §14.1)."""

from app.infrastructure.credentials import CredentialStore, issue_token


class TestIssueToken:
    def test_tokens_are_long_and_url_safe(self) -> None:
        token = issue_token()

        assert len(token) >= 40
        assert all(ch.isalnum() or ch in "-_" for ch in token)

    def test_tokens_are_unique(self) -> None:
        assert len({issue_token() for _ in range(200)}) == 200


class TestHostCredentials:
    def test_registered_host_token_verifies(self) -> None:
        store = CredentialStore()
        store.register_host("ABC234", "host-secret")

        assert store.verify_host("ABC234", "host-secret") is True

    def test_room_code_is_normalized(self) -> None:
        store = CredentialStore()
        store.register_host("abc234", "host-secret")

        assert store.verify_host(" ABC234 ", "host-secret") is True

    def test_wrong_missing_or_oversized_token_is_rejected(self) -> None:
        store = CredentialStore()
        store.register_host("ABC234", "host-secret")

        assert store.verify_host("ABC234", "wrong") is False
        assert store.verify_host("ABC234", "") is False
        assert store.verify_host("ABC234", None) is False
        assert store.verify_host("ABC234", "x" * 10_000) is False

    def test_unknown_room_is_rejected(self) -> None:
        assert CredentialStore().verify_host("ZZZZZ2", "anything") is False

    def test_host_token_is_not_valid_for_another_room(self) -> None:
        store = CredentialStore()
        store.register_host("ABC234", "host-secret")
        store.register_host("DEF567", "other-secret")

        assert store.verify_host("DEF567", "host-secret") is False

    def test_plaintext_token_is_never_stored(self) -> None:
        store = CredentialStore()
        store.register_host("ABC234", "host-secret-value")
        store.register_player("ABC234", "p1", "player-secret-value")

        stored = repr(vars(store))
        assert "host-secret-value" not in stored
        assert "player-secret-value" not in stored


class TestPlayerCredentials:
    def test_player_token_verifies_only_for_that_player(self) -> None:
        store = CredentialStore()
        store.register_player("ABC234", "p1", "token-1")
        store.register_player("ABC234", "p2", "token-2")

        assert store.verify_player("ABC234", "p1", "token-1") is True
        assert store.verify_player("ABC234", "p1", "token-2") is False
        assert store.verify_player("ABC234", "p3", "token-1") is False

    def test_forget_player(self) -> None:
        store = CredentialStore()
        store.register_player("ABC234", "p1", "token-1")

        store.forget_player("ABC234", "p1")

        assert store.verify_player("ABC234", "p1", "token-1") is False

    def test_forget_room_drops_host_and_players(self) -> None:
        store = CredentialStore()
        store.register_host("ABC234", "host")
        store.register_player("ABC234", "p1", "token-1")
        store.register_player("DEF567", "p9", "token-9")

        store.forget_room("abc234")

        assert store.verify_host("ABC234", "host") is False
        assert store.verify_player("ABC234", "p1", "token-1") is False
        assert store.verify_player("DEF567", "p9", "token-9") is True
