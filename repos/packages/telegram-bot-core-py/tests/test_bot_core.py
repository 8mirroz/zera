import unittest

from telegram_bot_core import MemoryIdempotencyStore, TelegramBotCoreSettings, make_dedupe_key, make_log_event, webhook_path


class TestBotCore(unittest.TestCase):
    def test_make_dedupe_key_is_stable(self) -> None:
        key_a = make_dedupe_key(user_id=7, action="checkout", payload="a=b")
        key_b = make_dedupe_key(user_id=7, action="checkout", payload="a=b")
        self.assertEqual(key_a, key_b)

    def test_memory_idempotency_store_detects_replay(self) -> None:
        store = MemoryIdempotencyStore()
        self.assertFalse(store.seen("x"))
        self.assertTrue(store.seen("x"))

    def test_webhook_path_normalizes_leading_slash(self) -> None:
        settings = TelegramBotCoreSettings.model_construct(
            bot_token="token",
            webhook_path_value="hook",
        )
        self.assertEqual(webhook_path(settings), "/hook")

    def test_log_event_contains_required_fields(self) -> None:
        event = make_log_event(
            event="handler_enter",
            correlation_id="corr-1",
            chat_id=1,
            user_id=2,
            handler="start_handler",
            dedupe_key="k",
        )
        self.assertEqual(event["event"], "handler_enter")
        self.assertEqual(event["correlation_id"], "corr-1")
        self.assertEqual(event["dedupe_key"], "k")


if __name__ == "__main__":
    unittest.main()
