"""apply_html_form and validate_completed_form: type-specific operations, each read back. Nothing here can press Submit."""
from __future__ import annotations

import re


def _locator(page, field):
    return page.frames[field.frame].locator(field.selector).first


def _radio(page, field, value) -> None:
    index = field.options.index(value)
    page.frames[field.frame].locator(field.selector).nth(index).check()


def apply_field(page, field, value) -> None:
    box = _locator(page, field)
    if field.type == "radio":
        _radio(page, field, value)
    elif field.type == "checks":
        for item in value:
            page.frames[field.frame].locator(field.selector).nth(field.options.index(item)).check()
    elif field.type == "checkbox":
        box.check() if str(value).lower() in ("true", "yes", "1") else box.uncheck()
    elif field.type == "select":
        box.select_option(label=value)
    elif field.type == "ariaradio":
        box.get_by_role("radio", name=value, exact=True).click()
    elif field.type == "combobox":
        box.click()
        box.fill(value)
        page.frames[field.frame].get_by_role("option", name=value, exact=True).first.click()
    elif field.type == "repeat":
        for index, row in enumerate(value):
            if index >= field.rows:
                box.click()
            scope = box.locator("xpath=ancestor::*[self::fieldset or self::div][.//input or .//textarea][1]")
            inputs = scope.locator("input,textarea")
            width = len(field.columns)
            for column, label in enumerate(field.columns):
                text = row.get(label, next((v for k, v in row.items() if k.lower() == label.lower()), ""))
                if text not in (None, ""):
                    inputs.nth(index * width + column).fill(str(text))
    else:
        box.fill(", ".join(map(str, value)) if isinstance(value, list) else str(value))


def same(field, wanted, got) -> bool:
    if field.type == "repeat":
        return len(got or []) >= len(wanted)
    if field.type == "checks":
        return set(got or []) == set(wanted)
    if field.type == "tel":  # masks reformat what was typed
        return re.sub(r"\D", "", str(got)).endswith(re.sub(r"\D", "", str(wanted))[-10:])
    if field.type == "checkbox":
        return bool(got) == (str(wanted).lower() in ("true", "yes", "1"))
    if isinstance(wanted, list):
        return str(got) == ", ".join(map(str, wanted))
    return str(got) == str(wanted)


def click_next(page) -> None:
    """Only a control the inspector marked as Next, and never a submit button."""
    target = page.frames[0].locator('[data-ff-next="1"]:not([type=submit])').first
    target.click()
    page.wait_for_timeout(150)
