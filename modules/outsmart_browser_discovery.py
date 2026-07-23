import asyncio
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from modules.config import PROJECT_ROOT
from modules.safety import READ_ONLY_GUARD

OUTSMART_EXPORT_DIR = PROJECT_ROOT / "outsmart_exports"
PROFILE_DIR = PROJECT_ROOT / "browser_profile_outsmart"

FORBIDDEN_BUTTON_WORDS = [
    "opslaan", "bewaren", "verwijderen", "delete", "aanmaken", "maken", "versturen",
    "verzenden", "factureren", "kopieren", "kopiëren", "status aanpassen", "uploaden",
    "archiveren", "importeren", "exporteren", "save", "submit", "send", "create",
]

SAFE_DROPDOWN_SELECTORS = [
    "select",
    "[role='combobox']",
    ".select2-selection",
    ".select2-choice",
    "button[aria-haspopup='listbox']",
    "input[aria-autocomplete]",
]


@dataclass
class DiscoverySnapshot:
    url: str
    title: str
    captured_at: str
    fields: List[Dict[str, object]]
    buttons: List[Dict[str, object]]
    links: List[Dict[str, object]]
    tables: List[Dict[str, object]]
    dropdowns: List[Dict[str, object]]


class OutSmartBrowserDiscovery:
    def __init__(self) -> None:
        READ_ONLY_GUARD.assert_read_only()
        OUTSMART_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    async def run_interactive(self) -> None:
        try:
            from playwright.async_api import async_playwright
        except Exception as exc:
            raise RuntimeError("Playwright is niet geïnstalleerd. Start install_workpc_requirements.bat.") from exc

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                str(PROFILE_DIR),
                headless=False,
                viewport={"width": 1440, "height": 950},
                accept_downloads=False,
            )
            page = context.pages[0] if context.pages else await context.new_page()
            if not page.url or page.url == "about:blank":
                await page.goto("https://app.out-smart.com/next/", wait_until="domcontentloaded")
            print("\nOutSmart Discovery gestart in READ-ONLY mode.")
            print("Log zelf in, navigeer naar een relevant scherm en druk hier op ENTER.")
            print("Commando's: ENTER = scan huidig scherm, q = stoppen")
            while True:
                command = input("scan> ").strip().lower()
                if command in {"q", "quit", "stop"}:
                    break
                await self.capture_page(page)
            await context.close()

    async def capture_page(self, page) -> Path:
        READ_ONLY_GUARD.assert_read_only()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = self._safe_name(await page.title() or "outsmart_page")
        folder = OUTSMART_EXPORT_DIR / f"{timestamp}_{name}"
        folder.mkdir(parents=True, exist_ok=True)
        await page.wait_for_timeout(1000)
        html = await page.content()
        (folder / "page.html").write_text(html, encoding="utf-8")
        await page.screenshot(path=str(folder / "screenshot.png"), full_page=True)
        snapshot = await self._extract_snapshot(page)
        (folder / "snapshot.json").write_text(json.dumps(asdict(snapshot), indent=4, ensure_ascii=False), encoding="utf-8")
        dropdowns = await self._discover_dropdowns(page, folder)
        snapshot.dropdowns.extend(dropdowns)
        (folder / "snapshot.json").write_text(json.dumps(asdict(snapshot), indent=4, ensure_ascii=False), encoding="utf-8")
        (folder / "SUMMARY.md").write_text(self._summary(snapshot), encoding="utf-8")
        print(f"Scan klaar: {folder}")
        return folder

    async def _extract_snapshot(self, page) -> DiscoverySnapshot:
        data = await page.evaluate(
            r"""
            () => {
              const visibleText = (el) => (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim();
              const cssPath = (el) => {
                if (el.id) return '#' + CSS.escape(el.id);
                const parts = [];
                while (el && el.nodeType === Node.ELEMENT_NODE && parts.length < 6) {
                  let part = el.nodeName.toLowerCase();
                  if (el.className && typeof el.className === 'string') {
                    const cls = el.className.trim().split(/\s+/).slice(0,2).map(c => '.' + CSS.escape(c)).join('');
                    part += cls;
                  }
                  parts.unshift(part);
                  el = el.parentElement;
                }
                return parts.join(' > ');
              };
              const fields = Array.from(document.querySelectorAll('input, textarea, select')).map(el => ({
                tag: el.tagName.toLowerCase(),
                type: el.getAttribute('type') || '',
                name: el.getAttribute('name') || '',
                id: el.id || '',
                label: el.labels && el.labels[0] ? el.labels[0].innerText.trim() : '',
                placeholder: el.getAttribute('placeholder') || '',
                value: el.value || '',
                required: !!el.required,
                disabled: !!el.disabled,
                readonly: !!el.readOnly,
                selector: cssPath(el),
                options: el.tagName.toLowerCase() === 'select' ? Array.from(el.options).map(o => ({value: o.value, text: o.text})) : []
              }));
              const buttons = Array.from(document.querySelectorAll('button, input[type=button], input[type=submit], a.btn, .btn')).map(el => ({
                text: visibleText(el),
                tag: el.tagName.toLowerCase(),
                type: el.getAttribute('type') || '',
                href: el.getAttribute('href') || '',
                selector: cssPath(el)
              }));
              const links = Array.from(document.querySelectorAll('a')).slice(0, 500).map(el => ({text: visibleText(el), href: el.href || '', selector: cssPath(el)}));
              const tables = Array.from(document.querySelectorAll('table')).map((table, idx) => ({
                index: idx,
                headers: Array.from(table.querySelectorAll('th')).map(th => th.innerText.trim()),
                rows: table.querySelectorAll('tr').length,
                selector: cssPath(table)
              }));
              return {fields, buttons, links, tables};
            }
            """
        )
        return DiscoverySnapshot(
            url=page.url,
            title=await page.title(),
            captured_at=datetime.now().isoformat(timespec="seconds"),
            fields=data["fields"],
            buttons=data["buttons"],
            links=data["links"],
            tables=data["tables"],
            dropdowns=[],
        )

    async def _discover_dropdowns(self, page, folder: Path) -> List[Dict[str, object]]:
        results: List[Dict[str, object]] = []
        handles = []
        for selector in SAFE_DROPDOWN_SELECTORS:
            try:
                handles.extend(await page.query_selector_all(selector))
            except Exception:
                pass
        for idx, handle in enumerate(handles[:80], start=1):
            try:
                text = (await handle.inner_text()) or ""
            except Exception:
                text = ""
            if self._looks_forbidden(text):
                continue
            try:
                box = await handle.bounding_box()
                if not box:
                    continue
                await handle.click(timeout=1200)
                await page.wait_for_timeout(400)
                options = await page.evaluate(
                    r"""
                    () => Array.from(document.querySelectorAll('.select2-results__option, .select2-result-label, [role=option], option, li')).slice(0, 300).map(el => ({
                      text: (el.innerText || el.textContent || '').trim(),
                      value: el.getAttribute('value') || el.getAttribute('data-value') || '',
                      role: el.getAttribute('role') || '',
                      className: el.className || ''
                    })).filter(x => x.text)
                    """
                )
                if options:
                    await page.screenshot(path=str(folder / f"dropdown_{idx:03d}.png"), full_page=True)
                    results.append({"index": idx, "trigger_text": text.strip()[:160], "options": options[:300]})
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(150)
            except Exception as exc:
                results.append({"index": idx, "trigger_text": text.strip()[:160], "error": str(exc)})
                try:
                    await page.keyboard.press("Escape")
                except Exception:
                    pass
        return results

    def _looks_forbidden(self, text: str) -> bool:
        lower = (text or "").lower()
        return any(word in lower for word in FORBIDDEN_BUTTON_WORDS)

    def _safe_name(self, value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "page").strip("._")
        return cleaned[:60] or "page"

    def _summary(self, snapshot: DiscoverySnapshot) -> str:
        lines = [
            "# OutSmart Browser Discovery Snapshot",
            "",
            f"URL: {snapshot.url}",
            f"Title: {snapshot.title}",
            f"Captured: {snapshot.captured_at}",
            "",
            f"Fields: {len(snapshot.fields)}",
            f"Buttons: {len(snapshot.buttons)}",
            f"Links: {len(snapshot.links)}",
            f"Tables: {len(snapshot.tables)}",
            f"Dropdown captures: {len(snapshot.dropdowns)}",
            "",
            "## Fields",
        ]
        for field in snapshot.fields[:200]:
            lines.append(f"- {field.get('label') or field.get('name') or field.get('id') or field.get('placeholder')} | {field.get('tag')} | {field.get('type')} | required={field.get('required')}")
        lines.extend(["", "## Dropdowns"])
        for dropdown in snapshot.dropdowns:
            lines.append(f"- {dropdown.get('trigger_text')} -> {len(dropdown.get('options', []))} options")
        return "\n".join(lines)


def run_outsmart_browser_discovery() -> None:
    asyncio.run(OutSmartBrowserDiscovery().run_interactive())


