import os
import sys
import json
import logging
from pathlib import Path

# Anki modüllerini içe aktar
from aqt import mw
from aqt.utils import showInfo, qconnect
from aqt.qt import *

# Kendi modüllerimizi içe aktaracağız
from . import ui
from . import logic

def run_smart_dedup():
    """Eklentiyi başlatan ana fonksiyon"""
    # API Key kontrolü
    config = mw.addonManager.getConfig(__name__)
    if not config or not config.get("openai_api_key"):
        showInfo("Lütfen önce Yapılandırma (Config) kısmından OpenAI API anahtarınızı girin.")
        return

    # Arayüzü başlat
    mw.smart_dedup_window = ui.SmartDedupWindow(mw)
    mw.smart_dedup_window.show()

def init_addon():
    """Anki menüsüne butonu ekler"""
    action = QAction("DUS Mentörü: Akıllı Tekilleştirme", mw)
    qconnect(action.triggered, run_smart_dedup)
    mw.form.menuTools.addAction(action)

init_addon()
