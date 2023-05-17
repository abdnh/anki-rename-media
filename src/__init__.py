import functools
from re import Match

from anki.collection import Collection, OpChanges, OpChangesWithCount
from aqt import gui_hooks, mw
from aqt.operations import CollectionOp
from aqt.qt import *
from aqt.utils import tooltip

try:
    from aqt.browser.browser import Browser
except ImportError:
    from aqt.browser import Browser


def on_rename(browser: Browser) -> None:
    def op(col: Collection) -> OpChanges:
        def rename_ref(match: Match, new_basename: str) -> str:
            fname = match.group("fname")
            basename, ext = os.path.splitext(fname)
            if new_basename == basename:
                return match.group(0)
            new_filename = f"{new_basename}{ext}"
            try:
                with open(os.path.join(col.media.dir(), fname), "rb") as file:
                    new_filename = col.media.write_data(new_filename, file.read())
            except FileNotFoundError:
                pass
            # TODO: maybe update references in any other notes too
            return match.group(0).replace(fname, new_filename)

        config = mw.addonManager.getConfig(__name__)
        media_field = config["media_field"]
        filename_field = config["filename_field"]
        filename_prefix = config["filename_prefix"]
        filename_suffix = config["filename_suffix"]

        nids = browser.selected_notes()
        updated_notes = []
        for nid in nids:
            note = col.get_note(nid)
            if media_field not in note or filename_field not in note:
                continue
            new_basename = filename_prefix + note[filename_field] + filename_suffix
            if not new_basename:
                continue

            note[media_field] = col.media.transform_names(
                note[media_field],
                functools.partial(rename_ref, new_basename=new_basename),
            )
            updated_notes.append(note)

        return OpChangesWithCount(
            changes=col.update_notes(updated_notes), count=len(updated_notes)
        )

    def on_success(changes: OpChangesWithCount) -> None:
        tooltip(f"Updated {changes.count} notes", parent=browser)

    CollectionOp(browser, op).success(on_success).run_in_background()


def add_browser_menu_item(browser: Browser) -> None:
    action = QAction("Rename Media", browser)
    qconnect(action.triggered, lambda: on_rename(browser))
    browser.form.menuEdit.addSeparator()
    browser.form.menuEdit.addAction(action)


gui_hooks.browser_menus_did_init.append(add_browser_menu_item)
