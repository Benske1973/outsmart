import asyncio
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

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
    ".select2-container",
    "button[aria-haspopup='listbox']",
    "input[aria-autocomplete]",
]

DROPDOWN_SEARCH_TERMS = [
    "", " ", "a", "e", "s", "g", "1", "2", "3", "4", "5",
    "Gent", "Scheldekenslaan", "Botermarkt", "Antonius", "Kortrijksesteenweg",
    "Jan Breydelstraat", "Farmanstraat", "Brandweer", "Mobiliteit", "Thuis",
    "G", "S.G", "S300", "G11", "G70",
]

SCROLL_STEPS = [0, 450, 900, 1400, 2000, 2800, 3800, 5200]


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
            context = await self._launch_context(p)
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


    async def connect_existing_chrome(self, cdp_url: str = "http://127.0.0.1:9222") -> None:
        try:
            from playwright.async_api import async_playwright
        except Exception as exc:
            raise RuntimeError("Playwright is niet geïnstalleerd. Start install_workpc_requirements.bat.") from exc

        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()
            print("\nVerbonden met bestaande Chrome in READ-ONLY mode.")
            print("Navigeer in die Chrome naar OutSmart. Druk hier op ENTER om het huidige tabblad te scannen.")
            print("Commando's: ENTER = scan huidig tabblad, deep = diepe read-only scan, nummer = kies tab, tabs = toon tabs, q = stoppen")
            while True:
                command = input("scan> ").strip().lower()
                if command in {"q", "quit", "stop"}:
                    break
                if command == "tabs":
                    pages = context.pages
                    for idx, tab in enumerate(pages):
                        print(f"{idx}: {await tab.title()} | {tab.url}")
                    continue
                if command in {"deep", "d", "diep"}:
                    await self.capture_page(page, deep=True)
                    continue
                if command.isdigit():
                    idx = int(command)
                    pages = context.pages
                    if 0 <= idx < len(pages):
                        page = pages[idx]
                        print(f"Geselecteerd: {await page.title()} | {page.url}")
                    else:
                        print("Ongeldig tabnummer")
                    continue
                await self.capture_page(page)
            await browser.close()

    async def _launch_context(self, playwright):
        launch_args = {
            "user_data_dir": str(PROFILE_DIR),
            "headless": False,
            "viewport": {"width": 1440, "height": 950},
            "accept_downloads": False,
        }
        for channel in ["chrome", "msedge"]:
            try:
                return await playwright.chromium.launch_persistent_context(channel=channel, **launch_args)
            except Exception:
                continue
        # Fallback: only works when Playwright browser binaries are installed.
        return await playwright.chromium.launch_persistent_context(**launch_args)

    async def capture_page(self, page, deep: bool = False) -> Path:
        READ_ONLY_GUARD.assert_read_only()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = self._safe_name(await page.title() or "outsmart_page")
        folder = OUTSMART_EXPORT_DIR / f"{timestamp}_{name}"
        folder.mkdir(parents=True, exist_ok=True)
        await page.wait_for_timeout(1000)
        html = await page.content()
        (folder / "page.html").write_text(html, encoding="utf-8")
        await page.screenshot(path=str(folder / "screenshot.png"), full_page=True)

        frame_snapshots = []
        for frame_index, frame in enumerate(page.frames):
            try:
                await frame.wait_for_load_state("domcontentloaded", timeout=1500)
            except Exception:
                pass
            try:
                frame_html = await frame.content()
                (folder / f"frame_{frame_index:02d}.html").write_text(frame_html, encoding="utf-8")
                frame_snapshot = await self._extract_frame_snapshot(frame, frame_index)
                frame_snapshots.append(asdict(frame_snapshot))
            except Exception as exc:
                frame_snapshots.append({
                    "frame_index": frame_index,
                    "url": getattr(frame, "url", ""),
                    "title": "",
                    "captured_at": datetime.now().isoformat(timespec="seconds"),
                    "fields": [],
                    "buttons": [],
                    "links": [],
                    "tables": [],
                    "dropdowns": [],
                    "error": str(exc),
                })

        snapshot = await self._extract_snapshot(page)
        dropdowns = await self._discover_dropdowns(page, folder, page=page, keyboard=page.keyboard, prefix="page", deep=deep)
        snapshot.dropdowns.extend(dropdowns)
        if deep:
            await self._scroll_context(page, page, folder, "page")
            for frame_index, frame in enumerate(page.frames):
                await self._scroll_context(frame, page, folder, f"frame_{frame_index:02d}")
            for frame_index, frame in enumerate(page.frames):
                frame_dropdowns = await self._discover_dropdowns(frame, folder, page=page, keyboard=page.keyboard, prefix=f"frame_{frame_index:02d}", deep=True)
                if frame_index < len(frame_snapshots):
                    frame_snapshots[frame_index].setdefault("dropdowns", []).extend(frame_dropdowns)
        snapshot_dict = asdict(snapshot)
        snapshot_dict["frames"] = frame_snapshots
        (folder / "snapshot.json").write_text(json.dumps(snapshot_dict, indent=4, ensure_ascii=False), encoding="utf-8")
        (folder / "SUMMARY.md").write_text(self._summary(snapshot, frame_snapshots), encoding="utf-8")
        print(f"Scan klaar: {folder}")
        return folder


    async def _extract_frame_snapshot(self, frame, frame_index: int) -> DiscoverySnapshot:
        data = await frame.evaluate(
            r"""
            () => {
              const visibleText = (el) => (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim();
              const cssPath = (el) => {
                if (el.id) return '#' + CSS.escape(el.id);
                const parts = [];
                while (el && el.nodeType === Node.ELEMENT_NODE && parts.length < 7) {
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
              const labelFor = (el) => {
                if (el.labels && el.labels[0]) return el.labels[0].innerText.trim();
                const id = el.id || '';
                if (id) {
                  const label = document.querySelector(`label[for="${CSS.escape(id)}"]`);
                  if (label) return label.innerText.trim();
                }
                const parent = el.closest('.form-group, .control-group, tr, div');
                if (parent) {
                  const label = parent.querySelector('label, .control-label, th, td:first-child');
                  if (label) return label.innerText.trim();
                }
                return '';
              };
              const fields = Array.from(document.querySelectorAll('input, textarea, select')).map(el => ({
                tag: el.tagName.toLowerCase(),
                type: el.getAttribute('type') || '',
                name: el.getAttribute('name') || '',
                id: el.id || '',
                label: labelFor(el),
                placeholder: el.getAttribute('placeholder') || '',
                value: el.value || '',
                required: !!el.required || el.getAttribute('aria-required') === 'true',
                disabled: !!el.disabled,
                readonly: !!el.readOnly,
                selector: cssPath(el),
                options: el.tagName.toLowerCase() === 'select' ? Array.from(el.options).map(o => ({value: o.value, text: o.text})) : []
              }));
              const buttons = Array.from(document.querySelectorAll('button, input[type=button], input[type=submit], a.btn, .btn')).map(el => ({
                text: visibleText(el), tag: el.tagName.toLowerCase(), type: el.getAttribute('type') || '', href: el.getAttribute('href') || '', selector: cssPath(el)
              }));
              const links = Array.from(document.querySelectorAll('a')).slice(0, 800).map(el => ({text: visibleText(el), href: el.href || '', selector: cssPath(el)}));
              const tables = Array.from(document.querySelectorAll('table')).map((table, idx) => ({
                index: idx, headers: Array.from(table.querySelectorAll('th')).map(th => th.innerText.trim()), rows: table.querySelectorAll('tr').length, selector: cssPath(table)
              }));
              return {fields, buttons, links, tables};
            }
            """
        )
        return DiscoverySnapshot(
            url=frame.url,
            title=f"frame_{frame_index}",
            captured_at=datetime.now().isoformat(timespec="seconds"),
            fields=data["fields"],
            buttons=data["buttons"],
            links=data["links"],
            tables=data["tables"],
            dropdowns=[],
        )

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

    async def _discover_dropdowns(self, context, folder: Path, page, keyboard, prefix: str = "page", deep: bool = False) -> List[Dict[str, object]]:
        results: List[Dict[str, object]] = []
        handles = []
        seen_selectors = set()
        for selector in SAFE_DROPDOWN_SELECTORS:
            try:
                for handle in await context.query_selector_all(selector):
                    try:
                        selector_key = await handle.evaluate("el => el.id || el.name || el.className || el.outerHTML.slice(0,120)")
                    except Exception:
                        selector_key = str(id(handle))
                    if selector_key in seen_selectors:
                        continue
                    seen_selectors.add(selector_key)
                    handles.append(handle)
            except Exception:
                pass
        limit = 160 if deep else 80
        for idx, handle in enumerate(handles[:limit], start=1):
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
                await handle.click(timeout=1400)
                await page.wait_for_timeout(500)
                options = await self._collect_visible_options(context)
                searches = []
                if deep:
                    searches = await self._probe_search_dropdown(context, page, keyboard)
                    merged = {(opt.get("text", ""), opt.get("value", "")): opt for opt in options}
                    for search in searches:
                        for opt in search.get("options", []):
                            merged[(opt.get("text", ""), opt.get("value", ""))] = opt
                    options = list(merged.values())
                if options or searches:
                    try:
                        await page.screenshot(path=str(folder / f"{prefix}_dropdown_{idx:03d}.png"), full_page=True)
                    except Exception:
                        pass
                    results.append({
                        "index": idx,
                        "context": prefix,
                        "trigger_text": text.strip()[:160],
                        "options": options[:1200],
                        "searches": searches[:80],
                    })
                await keyboard.press("Escape")
                await page.wait_for_timeout(150)
            except Exception as exc:
                results.append({"index": idx, "context": prefix, "trigger_text": text.strip()[:160], "error": str(exc)})
                try:
                    await keyboard.press("Escape")
                except Exception:
                    pass
        return results

    async def _collect_visible_options(self, context) -> List[Dict[str, object]]:
        return await context.evaluate(
            r"""
            () => Array.from(document.querySelectorAll('.select2-results__option, .select2-result-label, [role=option], option, li, .dropdown-item, .v-list-item')).slice(0, 1500).map(el => ({
              text: (el.innerText || el.textContent || '').trim(),
              value: el.getAttribute('value') || el.getAttribute('data-value') || el.getAttribute('data-id') || '',
              role: el.getAttribute('role') || '',
              className: el.className || ''
            })).filter(x => x.text && x.text.length < 300)
            """
        )

    async def _probe_search_dropdown(self, context, page, keyboard) -> List[Dict[str, object]]:
        searches: List[Dict[str, object]] = []
        for term in DROPDOWN_SEARCH_TERMS:
            try:
                search = await context.query_selector('.select2-search__field, .select2-input, input[role="searchbox"], input[type="search"]')
                if not search:
                    break
                await search.fill(term, timeout=900)
                await page.wait_for_timeout(650)
                options = await self._collect_visible_options(context)
                searches.append({"term": term, "option_count": len(options), "options": options[:250]})
            except Exception:
                break
        try:
            await keyboard.press("Escape")
        except Exception:
            pass
        return searches

    async def _scroll_context(self, context, page, folder: Path, prefix: str) -> None:
        for pos in SCROLL_STEPS:
            try:
                await context.evaluate("y => window.scrollTo(0, y)", pos)
                await page.wait_for_timeout(250)
                snapshot = await self._extract_frame_snapshot(context, 0) if prefix.startswith("frame_") else await self._extract_snapshot(page)
                out = folder / f"{prefix}_scroll_{pos}.json"
                out.write_text(json.dumps(asdict(snapshot), indent=4, ensure_ascii=False), encoding="utf-8")
            except Exception:
                continue

    def _looks_forbidden(self, text: str) -> bool:
        lower = (text or "").lower()
        return any(word in lower for word in FORBIDDEN_BUTTON_WORDS)

    def _safe_name(self, value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "page").strip("._")
        return cleaned[:60] or "page"

    def _summary(self, snapshot: DiscoverySnapshot, frame_snapshots: Optional[List[Dict[str, object]]] = None) -> str:
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
            f"Frames: {len(frame_snapshots or [])}",
            "",
            "## Fields",
        ]
        for field in snapshot.fields[:200]:
            lines.append(f"- {field.get('label') or field.get('name') or field.get('id') or field.get('placeholder')} | {field.get('tag')} | {field.get('type')} | required={field.get('required')}")
        lines.extend(["", "## Frames"])
        for frame in frame_snapshots or []:
            lines.append(f"- {frame.get('title')} | {frame.get('url')} | fields={len(frame.get('fields') or [])} | tables={len(frame.get('tables') or [])}")
        lines.extend(["", "## Dropdowns"])
        for dropdown in snapshot.dropdowns:
            lines.append(f"- {dropdown.get('trigger_text')} -> {len(dropdown.get('options', []))} options")
        return "\n".join(lines)


def run_outsmart_browser_discovery() -> None:
    asyncio.run(OutSmartBrowserDiscovery().run_interactive())





