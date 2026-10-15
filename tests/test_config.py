import unittest

from src.config import Settings


class SettingsFromEnvTest(unittest.TestCase):
    def test_canonical_provider_names_override_legacy_names(self) -> None:
        settings = Settings.from_env(
            {
                "LLM_API_KEY": "new-key",
                "DEEPSEEK_API_KEY": "old-key",
                "LLM_MODEL": "new-model",
                "DEEPSEEK_MODEL": "old-model",
                "LLM_BASE_URL": "https://new.example/v1",
                "DEEPSEEK_BASE_URL": "https://old.example/v1",
            }
        )

        self.assertEqual(settings.api_key, "new-key")
        self.assertEqual(settings.model, "new-model")
        self.assertEqual(settings.base_url, "https://new.example/v1")

    def test_legacy_provider_names_are_still_supported(self) -> None:
        settings = Settings.from_env(
            {
                "DEEPSEEK_API_KEY": "legacy-key",
                "DEEPSEEK_MODEL": "deepseek-chat",
                "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
            }
        )

        self.assertEqual(settings.api_key, "legacy-key")
        self.assertEqual(settings.model, "deepseek-chat")
        self.assertEqual(settings.base_url, "https://api.deepseek.com")

    def test_explicit_history_budget_overrides_calculation(self) -> None:
        settings = Settings(max_history_tokens=100)

        self.assertEqual(settings.resolve_history_token_budget(), 100)
        self.assertEqual(settings.resolve_history_token_budget(300), 300)

    def test_auto_history_budget_is_bounded_by_default(self) -> None:
        settings = Settings()

        self.assertEqual(settings.resolve_history_token_budget(), 2500)


if __name__ == "__main__":
    unittest.main()
