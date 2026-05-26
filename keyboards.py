"""
Keyboard builders - Separates UI logic from handlers.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import config


class Keyboards:
    """Keyboard builder utilities."""

    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Build main menu keyboard."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🧠 Choose Model",
                        callback_data="choose_model",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⭐ Buy Questions",
                        callback_data="buy_questions",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="💬 Ask Question",
                        callback_data="ask_question",
                    )
                ],
            ]
        )

    @staticmethod
    def models() -> InlineKeyboardMarkup:
        """Build model selection keyboard."""
        buttons = [
            [
                InlineKeyboardButton(
                    text=f"🤖 {key.upper()}",
                    callback_data=f"model_{key}",
                )
            ]
            for key in config.AVAILABLE_MODELS.keys()
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def payment_packages() -> InlineKeyboardMarkup:
        """Build payment packages keyboard."""
        packages = [
            (
                "small",
                f"⭐ {config.get_stars_for_package('small')} Stars "
                f"({config.get_questions_for_package('small')} questions)",
            ),
            (
                "medium",
                f"⭐ {config.get_stars_for_package('medium')} Stars "
                f"({config.get_questions_for_package('medium')} questions)",
            ),
            (
                "large",
                f"⭐ {config.get_stars_for_package('large')} Stars "
                f"({config.get_questions_for_package('large')} questions)",
            ),
        ]

        buttons = [
            [InlineKeyboardButton(text=label, callback_data=f"pay_{package}")]
            for package, label in packages
        ]
        buttons.append([InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def cancel_button() -> InlineKeyboardMarkup:
        """Build cancel button."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
            ]
        )

    @staticmethod
    def buy_button() -> InlineKeyboardMarkup:
        """Build buy button."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⭐ Buy Questions", callback_data="buy_questions")]
            ]
        )
