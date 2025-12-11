"""WEKO metadata form utilities for E2E tests (2025 version).

This module provides utilities for filling and reading WEKO metadata forms.
Two distinct form types are supported:

- ProjectMetadataForm: Project-level metadata (funding, project name, etc.)
- FileMetadataForm: File/folder-level metadata (data title, description, creators, etc.)

Design principles:
- Each method performs exactly one action, no fallbacks
- If fallback is needed, caller handles it explicitly
- No .first/.last - use explicit indices
- No conditional branches that hide unexpected behavior
- Use actual label text as keys
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict


class FieldType(Enum):
    """Metadata field input types."""

    INPUT = "input"
    INPUT_DIRECT = "input_direct"
    TEXTAREA = "textarea"
    SELECT = "select"
    POWER_SELECT = "power_select"
    TABLE = "table"


class ProjectMetadataForm:
    """Project metadata form (GRDM metadata registration page).

    XPath base: //*[contains(text(), "{label}")]/../following-sibling::...
    """

    FIELDS: Dict[str, FieldType] = {
        "資金配分機関情報": FieldType.POWER_SELECT,
        "体系的番号におけるプログラム情報コード": FieldType.INPUT,
        "プログラム名 (日本語)": FieldType.INPUT,
        "Program name (English)": FieldType.INPUT,
        "体系的番号": FieldType.POWER_SELECT,
        "プロジェクト名 (日本語)": FieldType.INPUT,
        "Project name (English)": FieldType.INPUT,
        "プロジェクトの分野": FieldType.POWER_SELECT,
    }

    def __init__(self, page, parent_locator=None):
        self.page = page
        self._root = parent_locator or page

    def _get_locator(self, label: str, field_type: FieldType):
        base = "//*"
        match field_type:
            case FieldType.INPUT:
                return self._root.locator(
                    f'{base}[contains(text(), "{label}")]/../following-sibling::div[1]//input'
                )
            case FieldType.POWER_SELECT:
                return self._root.locator(
                    f'{base}[contains(text(), "{label}")]/../following-sibling::div[1]'
                )
            case _:
                raise ValueError(f"Unsupported field type: {field_type}")

    def get_locator(self, label: str):
        """Get the locator for a field."""
        field_type = self.FIELDS[label]
        return self._get_locator(label, field_type)

    async def fill(self, label: str, value: str) -> None:
        """Fill a field with a value."""
        field_type = self.FIELDS[label]
        locator = self._get_locator(label, field_type)

        match field_type:
            case FieldType.INPUT:
                await locator.clear()
                await locator.fill(value)
            case FieldType.POWER_SELECT:
                await locator.locator(".ember-power-select-trigger").click()
                option = self._root.locator(
                    f'//li[contains(@class, "ember-power-select-option") and contains(., "{value}")]'
                )
                await option.click()

    async def get(self, label: str) -> str:
        """Get the current value of a field."""
        field_type = self.FIELDS[label]
        locator = self._get_locator(label, field_type)

        match field_type:
            case FieldType.INPUT:
                return await locator.input_value()
            case FieldType.POWER_SELECT:
                return await locator.locator(".ember-power-select-selected-item").text_content()

    async def fill_power_select_by_search(self, label: str, value: str) -> None:
        """Fill a power-select by typing in search box (alternative to fill)."""
        field_type = self.FIELDS[label]
        locator = self._get_locator(label, field_type)
        await locator.locator(".ember-power-select-trigger").click()
        search = self._root.locator(".ember-power-select-search-input")
        await search.fill(value)
        await search.press("Enter")


class FileMetadataForm:
    """File/folder metadata form (metadata edit dialog).

    XPath base: //label[contains(text(), "{label}")]/../following-sibling::...
    """

    FIELDS: Dict[str, FieldType] = {
        # Basic info
        "ファイル種別": FieldType.SELECT,
        "データ No.": FieldType.INPUT,
        "データの名称または論文表題 (日本語)": FieldType.INPUT,
        "Title (English)": FieldType.INPUT,
        "掲載日・掲載更新日": FieldType.INPUT_DIRECT,
        "データの説明 (日本語)": FieldType.TEXTAREA,
        "Description (English)": FieldType.TEXTAREA,
        # Classification
        "データの分野": FieldType.SELECT,
        "データ種別": FieldType.SELECT,
        "概略データ量": FieldType.INPUT,  # special xpath handled in _get_locator
        # License and policy
        "管理対象データの利活用・提供方針 (有償/無償)": FieldType.SELECT,
        "管理対象データの利活用・提供方針 (ライセンス)": FieldType.SELECT,
        "管理対象データの利活用・提供方針 (引用方法等・日本語)": FieldType.TEXTAREA,
        "Data utilization and provision policy (citation information, English)": FieldType.TEXTAREA,
        # Access
        "アクセス権": FieldType.SELECT,
        "公開予定日": FieldType.INPUT_DIRECT,
        # Repository
        "リポジトリ情報 (日本語)": FieldType.INPUT,
        "Repository information (English)": FieldType.INPUT,
        "リポジトリURL・DOIリンク": FieldType.INPUT,
        # Creators
        "データ作成者": FieldType.TABLE,
        "著者名": FieldType.TABLE,
        # Hosting institution
        "データ管理機関 (日本語)": FieldType.INPUT,
        "Hosting institution (English)": FieldType.INPUT,
        "データ管理機関コード": FieldType.INPUT,
        # Bibliographic specific fields
        "論文（出版社版）のDOI": FieldType.INPUT,
        "論文の種類": FieldType.SELECT,
        "掲載誌名 (日本語)": FieldType.INPUT,
        "Journal Name (English)": FieldType.INPUT,
        "発行年月": FieldType.INPUT,
        "巻": FieldType.INPUT,
        "号": FieldType.INPUT,
        "掲載ページ (開始)": FieldType.INPUT,
        "掲載ページ (終了)": FieldType.INPUT,
        "学術論文を掲載した「機関リポジトリ等の情報基盤」のDOI": FieldType.INPUT,
        # Data manager
        "データ管理者の種類": FieldType.SELECT,
        "データ管理者の e-Rad 研究者番号": FieldType.INPUT,
        "データ管理者 (日本語)": FieldType.INPUT,
        "Data manager (English)": FieldType.INPUT,
        "データ管理者の所属組織名 (日本語)": FieldType.INPUT,
        "Contact organization of data manager (English)": FieldType.INPUT,
        "データ管理者の所属機関の連絡先住所 (日本語)": FieldType.INPUT,
        "Contact address of data manager (English)": FieldType.INPUT,
        "データ管理者の所属機関の連絡先電話番号": FieldType.INPUT,
        "データ管理者の所属機関の連絡先メールアドレス": FieldType.INPUT,
        # Remarks
        "備考 (日本語)": FieldType.TEXTAREA,
        "Remarks (English)": FieldType.TEXTAREA,
        # Metadata access
        "メタデータのアクセス権": FieldType.SELECT,
        # Publication specific extra
        "査読の有無": FieldType.SELECT,
        "版情報": FieldType.SELECT,
    }

    def __init__(self, page, parent_locator=None):
        self.page = page
        self._root = parent_locator or page

    def _get_locator(self, label: str, field_type: FieldType):
        # Special case: 概略データ量 has different xpath
        if label == "概略データ量":
            return self._root.locator(
                '//label[contains(text(), "概略データ量")]/../..//input[contains(@class, "form-control")]'
            )
        exact_labels = {"号"}
        if label in exact_labels:
            label_xpath = f'//label[normalize-space(.) = "{label}"]'
        else:
            label_xpath = f'//label[contains(text(), "{label}")]'

        match field_type:
            case FieldType.INPUT:
                return self._root.locator(
                    f'{label_xpath}/../following-sibling::div[1]//input'
                )
            case FieldType.INPUT_DIRECT:
                return self._root.locator(
                    f'{label_xpath}/../following-sibling::input[1]'
                )
            case FieldType.TEXTAREA:
                return self._root.locator(
                    f'{label_xpath}/../following-sibling::textarea[1]'
                )
            case FieldType.SELECT:
                if label == "アクセス権":
                    return self._root.locator(
                        f'//label[normalize-space(text())="{label}"]/../following-sibling::select[1]'
                    )
                return self._root.locator(
                    f'{label_xpath}/../following-sibling::select[1]'
                )
            case FieldType.TABLE:
                return self._root.locator(
                    f'{label_xpath}/../following-sibling::div[1]'
                )
            case _:
                raise ValueError(f"Unsupported field type: {field_type}")

    def get_locator(self, label: str):
        """Get the locator for a field."""
        field_type = self.FIELDS[label]
        return self._get_locator(label, field_type)

    async def fill(self, label: str, value: str) -> None:
        """Fill a field with a value (not for TABLE type)."""
        field_type = self.FIELDS[label]
        locator = self._get_locator(label, field_type)

        match field_type:
            case FieldType.INPUT | FieldType.INPUT_DIRECT:
                await locator.clear()
                await locator.fill(value)
            case FieldType.TEXTAREA:
                await locator.clear()
                await locator.fill(value)
            case FieldType.SELECT:
                await locator.select_option(label=value)
            case FieldType.TABLE:
                raise ValueError("Use table methods for TABLE type fields")

    async def get(self, label: str) -> str:
        """Get the current value of a field (not for TABLE type)."""
        field_type = self.FIELDS[label]
        locator = self._get_locator(label, field_type)

        match field_type:
            case FieldType.INPUT | FieldType.INPUT_DIRECT | FieldType.TEXTAREA:
                return await locator.input_value()
            case FieldType.SELECT:
                return await locator.locator("option:checked").text_content()
            case FieldType.TABLE:
                raise ValueError("Use table methods for TABLE type fields")

    async def scroll_to(self, label: str) -> None:
        """Scroll to make a field visible."""
        field_type = self.FIELDS[label]
        locator = self._get_locator(label, field_type)
        await locator.scroll_into_view_if_needed()

    # Table operations

    async def get_table_row_count(self, label: str) -> int:
        """Get the number of rows in a table field."""
        locator = self._get_locator(label, FieldType.TABLE)
        return await locator.locator("table tbody tr").count()

    async def click_table_add_row(self, label: str) -> None:
        """Click the add row button in a table field."""
        locator = self._get_locator(label, FieldType.TABLE)
        await locator.locator("a:has(i.fa-plus)").click()

    async def click_table_remove_row(self, label: str, row_index: int) -> None:
        """Click the remove button for a specific row (0-indexed)."""
        locator = self._get_locator(label, FieldType.TABLE)
        row = locator.locator(f"table tbody tr:nth-of-type({row_index + 1})")
        await row.locator(".remove-row i, span.remove-row i").click()

    async def fill_table_cell(self, label: str, row_index: int, col_index: int, value: str) -> None:
        """Fill a specific cell in a table field (0-indexed)."""
        locator = self._get_locator(label, FieldType.TABLE)
        row = locator.locator(f"table tbody tr:nth-of-type({row_index + 1})")
        cell_input = row.locator(f"td:nth-of-type({col_index + 1}) input")
        await cell_input.fill(value)

    async def get_table_cell(self, label: str, row_index: int, col_index: int) -> str:
        """Get value from a specific cell in a table field (0-indexed)."""
        locator = self._get_locator(label, FieldType.TABLE)
        row = locator.locator(f"table tbody tr:nth-of-type({row_index + 1})")
        cell_input = row.locator(f"td:nth-of-type({col_index + 1}) input")
        return await cell_input.input_value()

    async def fill_author(self, author: Dict[str, Any]) -> None:
        """Add an author row and fill all author fields."""
        container = self.get_locator("著者名")
        await self.click_table_add_row("著者名")

        edit_rows = container.locator('.metadata-edit-mode')
        row_count = await edit_rows.count()
        if row_count == 0:
            raise AssertionError("No edit rows found for authors")
        panel = edit_rows.nth(row_count - 1)
        await panel.wait_for(state="visible")

        await panel.locator('label:has-text("e-Rad 研究者番号") + div input').fill(author['number'])

        ja_inputs = panel.locator('label:has-text("名前(日本語)") + div table input')
        await ja_inputs.nth(0).fill(author['name_ja']['last'])
        await ja_inputs.nth(1).fill(author['name_ja']['middle'])
        await ja_inputs.nth(2).fill(author['name_ja']['first'])

        en_inputs = panel.locator('label:has-text("Name (English)") + div table input')
        await en_inputs.nth(0).fill(author['name_en']['last'])
        await en_inputs.nth(1).fill(author['name_en']['middle'])
        await en_inputs.nth(2).fill(author['name_en']['first'])

        await panel.locator('label:has-text("所属機関名(日本語)") + div input').fill(author['affiliation_ja'])
        await panel.locator('label:has-text("所属機関名(英語)") + div input').fill(author['affiliation_en'])

        await panel.locator('.hide-edit-row').click()
