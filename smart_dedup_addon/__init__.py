from aqt import mw
from aqt.utils import showInfo, qconnect
from aqt.qt import QAction
from . import ui


def run_smart_dedup():
    config = mw.addonManager.getConfig(__name__)
    if not config or not config.get("openai_api_key"):
        showInfo("Lütfen önce Yapılandırma (Config) kısmından OpenAI API anahtarınızı girin.")
        return

    if hasattr(mw, "smart_dedup_window") and mw.smart_dedup_window:
        mw.smart_dedup_window.show()
        mw.smart_dedup_window.raise_()
        mw.smart_dedup_window.activateWindow()
    else:
        mw.smart_dedup_window = ui.SmartDedupWindow(mw)
        mw.smart_dedup_window.show()


def init_addon():
    action = QAction("DUS Mentörü: Akıllı Tekilleştirme", mw)
    qconnect(action.triggered, run_smart_dedup)
    mw.form.menuTools.addAction(action)


init_addon()
