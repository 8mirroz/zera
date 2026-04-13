import unittest

from telegram_payments_core import PaymentStateMachine, PaymentTransitionError, normalize_payment_event, should_fulfill


class TestPaymentsCore(unittest.TestCase):
    def test_payment_state_machine_happy_path(self) -> None:
        machine = PaymentStateMachine()
        state = machine.apply("created", "pending")
        state = machine.apply(state, "confirmed")
        state = machine.apply(state, "fulfilled")
        self.assertEqual(state, "fulfilled")

    def test_payment_state_machine_rejects_invalid_transition(self) -> None:
        machine = PaymentStateMachine()
        with self.assertRaises(PaymentTransitionError):
            machine.apply("created", "confirmed")

    def test_normalize_payment_event_builds_idempotency_key(self) -> None:
        event = normalize_payment_event(
            provider="stripe",
            order_id="o-1",
            provider_event_id="evt-1",
            status_from="pending",
            status_to="confirmed",
            amount_minor=100,
            currency="USD",
            payload={"ok": True},
        )
        self.assertEqual(event["idempotency_key"], "o-1:evt-1:confirmed")

    def test_should_fulfill_only_after_confirmation(self) -> None:
        self.assertTrue(should_fulfill("confirmed").should_fulfill)
        self.assertFalse(should_fulfill("pending").should_fulfill)


if __name__ == "__main__":
    unittest.main()
