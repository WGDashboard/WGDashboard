#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class Language:
    """Represents a language configuration."""
    lang_id: str
    lang_name: str

    @classmethod
    def from_dict(cls, data: Dict) -> 'Language':
        """Create Language instance from dictionary."""
        return cls(
            lang_id=data.get('lang_id', ''),
            lang_name=data.get('lang_name', '')
        )


@dataclass
class TranslationStats:
    """Statistics about translation verification."""
    missing_count: int
    deprecated_count: int
    total_keys: int

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_keys == 0:
            return 0.0

        completed = self.total_keys - self.missing_count

        return (completed / self.total_keys) * 100


class LocaleManager:
    """Manages locale files and translation verification."""

    SUPPORTED_LOCALES_FILE = "supported_locales.json"
    LOCALE_TEMPLATE_FILE = "locale_template.json"

    def __init__(self):
        self.supported_locales: List[Language] = []
        self.locale_template: Dict[str, str] = {}
        self._load_configuration()

    def _load_configuration(self) -> None:
        """Load active languages and template configuration."""
        try:

            self.supported_locales = self._load_supported_locales()
            self.locale_template = self._load_locale_template()

        except FileNotFoundError as e:
            print(f"[✗] Configuration file not found: {e}")
            sys.exit(1)

        except json.JSONDecodeError as e:
            print(f"[✗] Invalid JSON in configuration file: {e}")
            sys.exit(1)

    def _load_supported_locales(self) -> List[Language]:
        """Load active languages from JSON file."""
        config_path = Path(self.SUPPORTED_LOCALES_FILE)

        if not config_path.exists():
            raise FileNotFoundError(
                f"Active languages file not found: {config_path}"
            )

        with open(config_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        return [Language.from_dict(lang_data) for lang_data in data]

    def _load_locale_template(self) -> Dict[str, str]:
        """Load language template from JSON file."""
        template_path = Path(self.LOCALE_TEMPLATE_FILE)

        if not template_path.exists():
            raise FileNotFoundError(
                f"Language template file not found: {template_path}"
            )

        with open(template_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def _load_language_file(self, lang_id: str) -> Dict[str, str]:
        """Load specific language file."""
        lang_path = Path(f"{lang_id}.json")

        if not lang_path.exists():
            raise FileNotFoundError(f"Language file not found: {lang_path}")

        with open(lang_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def _save_language_file(self, lang_id: str, lang_data: Dict[str, str]) -> None:
        """Save language file with proper formatting."""
        lang_path = Path(f"{lang_id}.json")

        with open(lang_path, 'w', encoding='utf-8') as file:
            json.dump(
                lang_data,
                file,
                ensure_ascii=False,
                indent='\t',
                sort_keys=True
            )

    def get_language_ids(self) -> List[str]:
        """Get list of all available language IDs."""
        return [lang.lang_id for lang in self.supported_locales]

    def validate_language_id(self, lang_id: str) -> Tuple[bool, str]:
        """
        Validate language ID.

        Returns:
            Tuple of (is_valid, error_message)
        """
        available_ids = self.get_language_ids()

        if lang_id not in available_ids:
            return False, f"'{lang_id}' is not a valid language ID"

        return True, ""

    def analyze_translations(self, lang_id: str) -> Tuple[List[str], List[str], TranslationStats]:
        """
        Analyze translation file for missing and deprecated keys.

        Returns:
            Tuple of (missing_keys, deprecated_keys, stats)
        """
        try:
            lang_file = self._load_language_file(lang_id)

        except FileNotFoundError:
            print(
                f"[!]  Language file {lang_id}.json not found. Creating new file..."
            )
            lang_file = {}

        # Find missing translations
        missing_translations = [
            key for key in self.locale_template
            if key not in lang_file or not lang_file[key].strip()
        ]

        # Find deprecated translations
        deprecated_translations = [
            key for key in lang_file
            if key not in self.locale_template
        ]

        # Calculate statistics
        stats = TranslationStats(
            missing_count=len(missing_translations),
            deprecated_count=len(deprecated_translations),
            total_keys=len(self.locale_template)
        )

        return missing_translations, deprecated_translations, stats

    def fix_translation_file(self, lang_id: str) -> TranslationStats:
        """
        Fix translation file by adding missing keys and removing deprecated ones.

        Returns:
            TranslationStats with the changes made
        """
        try:
            lang_file = self._load_language_file(lang_id)

        except FileNotFoundError:
            lang_file = {}

        missing_translations, deprecated_translations, stats = self.analyze_translations(
            lang_id
        )

        # Create new language file
        new_lang_file = dict(lang_file)

        # Add missing translations with empty values
        for key in missing_translations:
            new_lang_file[key] = ""

        # Remove deprecated translations
        for key in deprecated_translations:
            new_lang_file.pop(key, None)

        # Save updated file
        self._save_language_file(lang_id, new_lang_file)

        return stats

    def display_header(self) -> None:
        """Display application header."""
        title = "WGDashboard Locale File Manager [by @donaldzou]"
        border = "=" * (len(title) + 4)

        print(border)
        print(f"| {title} |")
        print(border)
        print()

    def display_available_languages(self) -> None:
        """Display available languages in a formatted table."""
        print("[i] Available languages")
        print("-" * 50)

        for lang in self.supported_locales:
            print(f"{lang.lang_id} | {lang.lang_name}")

        print()

    def display_translation_results(self, lang_id: str, stats: TranslationStats) -> None:
        """Display translation verification results."""
        print(f"[#] Translation analysis for '{lang_id}'")
        print("-" * 50)

        print(f"   [-] Total keys: {stats.total_keys}")
        print(f"   [✗] Missing translations: {stats.missing_count}")
        print(f"   [*] Deprecated translations: {stats.deprecated_count}")
        print(f"   [✓] Completion: {stats.completion_percentage:.1f}%")

        if stats.missing_count > 0 or stats.deprecated_count > 0:
            print(f"\n   [i]  File {lang_id}.json has been updated:")
            print(f"      • Missing translations added (empty values)")
            print(f"      • Deprecated translations removed")
        else:
            print(f"\n   Perfect! No issues found in {lang_id}.json")

        print()

    def get_user_language_choice(self) -> str:
        """Get language choice from user with validation."""
        while True:
            try:
                lang_id = input("[ENTER] Language ID to verify: ").strip()

                if not lang_id:
                    print("   [!]  Please enter a valid language ID")
                    continue

                is_valid, error_msg = self.validate_language_id(lang_id)

                if not is_valid:
                    print(f"   [✗] {error_msg}")
                    continue

                return lang_id

            except KeyboardInterrupt:
                print("\n\n[EXIT] Operation cancelled by user")
                sys.exit(0)

            except EOFError:
                print("\n\n[EXIT] Goodbye!")
                sys.exit(0)

    def run(self) -> None:
        """Main application loop."""
        try:
            self.display_header()
            self.display_available_languages()

            while True:
                lang_id = self.get_user_language_choice()

                print(f"\n[>] Verifying language file: {lang_id}.json")
                print("=" * 50)

                stats = self.fix_translation_file(lang_id)
                self.display_translation_results(lang_id, stats)

        except KeyboardInterrupt:
            print("\n\n[EXIT] Operation cancelled by user")
            sys.exit(0)

        except Exception as e:
            print(f"\n[✗] Unexpected error: {e}")
            sys.exit(1)


def main() -> None:
    """Entry point of the application."""
    locale_manager = LocaleManager()
    locale_manager.run()


if __name__ == "__main__":
    main()
