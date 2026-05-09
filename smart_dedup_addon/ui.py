import re
import threading
from aqt.qt import *
from aqt import mw
from .logic import SmartDedupLogic

class WorkerThread(QThread):
    finished = pyqtSignal(object)
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
        except Exception as e:
            result = e
        self.finished.emit(result)


class NamespaceSelectorDialog(QDialog):
    def __init__(self, namespaces, suggested_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Namespace Seç / Oluştur")
        self.setMinimumWidth(350)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Pinecone Namespace seçin veya yeni isim yazın:"))
        self.combo = QComboBox()
        self.combo.setEditable(True)
        # Pinecone'dan gelen isimleri küçük harfe çevirip tekilleştiriyoruz
        clean_namespaces = sorted(list(set(ns.lower() for ns in namespaces)))
        self.combo.addItems(clean_namespaces)
        self.combo.setCurrentText(suggested_name)
        layout.addWidget(self.combo)

        layout.addWidget(
            QLabel(
                "<small><i>Not: Yerel JSON dosyası da bu isimle (Örn: protez.json) oluşacaktır.</i></small>"
            )
        )

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_namespace(self):
        ns = self.combo.currentText()
        # Küçük harf zorunlu: Pinecone büyük/küçük harf duyarlı olduğu için karışıklığı önler.
        return re.sub(r"[^a-zA-Z0-9_-]", "_", ns).lower()[:100]


class SmartDedupWindow(QDialog):
    progress_signal = pyqtSignal(int)
    PAGE_SIZE = 50

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DUS Mentörü - Akıllı Tekilleştirme v2")
        self.setMinimumSize(900, 700)
        self.all_cards = []
        self.all_embeddings = []
        self.current_namespace = None
        self.logic = None
        self.setModal(False)
        self.is_running = False
        self.final_results = []
        self.card_checkboxes = {}
        self._all_results_to_display = []
        self._displayed_count = 0
        self._load_more_btn = None

        root = QVBoxLayout(self)

        top = QHBoxLayout()
        self.deck_combo = QComboBox()
        self.deck_combo.addItems(mw.col.decks.all_names())
        self.start_btn = QPushButton("İşlemi Başlat")
        self.start_btn.clicked.connect(self.start_process)
        top.addWidget(self.start_btn)

        self.sync_btn = QPushButton("Buluttan Önbelleği Senkronize Et (Maliyeti Azaltır)")
        self.sync_btn.setToolTip("Pinecone'da olan ama yerelde olmayan vektörleri çeker.")
        self.sync_btn.clicked.connect(self.sync_from_cloud)
        top.addWidget(self.sync_btn)

        self.bulk_delete_btn = QPushButton("SEÇİLİ KARTLARI SİL")
        self.bulk_delete_btn.clicked.connect(self._on_bulk_delete)
        self.bulk_delete_btn.setEnabled(False)
        self.bulk_delete_btn.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")

        self.seal_btn = QPushButton("Mühürle ve Pinecone'a Yükle")
        self.seal_btn.clicked.connect(self.seal_and_upload)
        self.seal_btn.setEnabled(False)
        self.seal_btn.setStyleSheet(
            "background-color: #f39c12; color: white; font-weight: bold;"
        )
        top.addWidget(QLabel("Deste:"))
        top.addWidget(self.deck_combo)
        # start_btn ve sync_btn zaten top'a eklendi
        top.addWidget(self.bulk_delete_btn)
        top.addWidget(self.seal_btn)
        root.addLayout(top)

        self.progress = QProgressBar()
        self.progress_signal.connect(self.progress.setValue)
        root.addWidget(self.progress)
        self.status_label = QLabel("Başlamak için deste seçip butona basın.")
        root.addWidget(self.status_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.content_widget)
        root.addWidget(scroll)

    # ── Start ─────────────────────────────────────────────────────────────────

    def start_process(self):
        config = mw.addonManager.getConfig(__name__)
        api_key = config.get("openai_api_key", "")
        pc_key = config.get("pinecone_api_key", "")
        pc_host = config.get("pinecone_index_host", "")
        threshold = float(config.get("similarity_threshold", 0.88))
        allowed_models = config.get("allowed_models", ["cloze-maxx", "basic-anking"])

        if not api_key or not api_key.strip() or "YOUR-SK" in api_key.upper():
            QMessageBox.warning(self, "Hata", "Lütfen geçerli bir OpenAI API anahtarı girin.")
            return

        # 1. Namespace seçimi
        tmp_logic = SmartDedupLogic(api_key, threshold=threshold, allowed_models=allowed_models)
        existing_ns = tmp_logic.get_pinecone_namespaces(pc_key, pc_host) if pc_key and pc_host else []

        deck_name = self.deck_combo.currentText()
        # Önerilen ismi de küçük harf yapalım
        suggested_ns = re.sub(r"[^a-zA-Z0-9_-]", "_", deck_name.split("::")[0]).lower()[:100]

        ns_dialog = NamespaceSelectorDialog(existing_ns, suggested_ns, self)
        if ns_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.current_namespace = ns_dialog.get_namespace()
        self.logic = tmp_logic
        self.start_btn.setEnabled(False)
        self.seal_btn.setEnabled(False)
        self.status_label.setText("Deste taranıyor...")

        # 2. DB erişimi — ana thread (thread-safe)
        try:
            cards = self.logic.get_cards_from_deck(deck_name)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Deste okuma hatası: {e}")
            self.start_btn.setEnabled(True)
            return

        if not cards:
            tip = (
                f"Destede uygun kart bulunamadı.\n\n"
                f"İzin verilen model tipleri: {', '.join(allowed_models)}\n"
                f"Kart tiplerini config'den değiştirebilirsiniz."
            )
            QMessageBox.information(self, "Bilgi", tip)
            self.start_btn.setEnabled(True)
            return

        self.all_cards = cards
        self.is_running = True
        threading.Thread(
            target=self._process_thread, args=(cards,), daemon=True
        ).start()

    # ── Background thread ─────────────────────────────────────────────────────

    def _process_thread(self, cards):
        try:
            cache = self.logic.load_cache(self.current_namespace)
            cached_count = 0

            all_embeddings = [None] * len(cards)
            to_vec_indices = []
            to_vec_texts = []

            for i, card in enumerate(cards):
                guid = card["guid"]
                text_hash = SmartDedupLogic._text_hash(card["text_to_vector"])
                entry = cache.get(guid)
                if isinstance(entry, dict) and entry.get("h") == text_hash:
                    all_embeddings[i] = entry["emb"]
                    cached_count += 1
                else:
                    to_vec_indices.append(i)
                    to_vec_texts.append(card["text_to_vector"])

            total_new = len(to_vec_texts)

            if cached_count:
                self._ui(f"Önbellekten {cached_count} kart yüklendi.", 10)

            if total_new:
                self._ui(f"{total_new} yeni kart vektörleniyor...", 15)
                BATCH = 100

                for batch_start in range(0, total_new, BATCH):
                    batch_end = min(batch_start + BATCH, total_new)
                    batch_texts = to_vec_texts[batch_start:batch_end]
                    batch_indices = to_vec_indices[batch_start:batch_end]

                    pct = 15 + int((batch_start / total_new) * 35)
                    self._ui(
                        f"Vektörleniyor: {batch_start + len(batch_texts)}/{total_new}...", pct
                    )

                    # Retry logic is inside get_embeddings
                    batch_embeddings = self.logic.get_embeddings(batch_texts)

                    if len(batch_embeddings) != len(batch_texts):
                        raise Exception("Eksik embedding yanıtı alındı.")

                    batch_cache = {}
                    for k, emb in enumerate(batch_embeddings):
                        gi = batch_indices[k]
                        all_embeddings[gi] = emb
                        text_hash = SmartDedupLogic._text_hash(cards[gi]["text_to_vector"])
                        batch_cache[cards[gi]["guid"]] = {"h": text_hash, "emb": emb}

                    # Atomic checkpoint — survives power loss between batches
                    self.logic.save_cache(self.current_namespace, batch_cache)

            self.all_embeddings = all_embeddings
            self._ui("Benzerlik analizi yapılıyor...", 52)

            def _sim_progress(done, total):
                pct = 52 + int((done / total) * 43)
                self._ui(f"Analiz: {done}/{total} chunk...", pct)

            pairs = self.logic.find_duplicates(cards, all_embeddings, _sim_progress)

            self._ui(f"Tamamlandı! {len(pairs)} aday bulundu.", 100)

            def _on_finish():
                from aqt.utils import showInfo
                showInfo(
                    f"Akıllı Tekilleştirme Tamamlandı!\n\n"
                    f"Namespace: {self.current_namespace}\n"
                    f"Toplam kart: {len(cards)}\n"
                    f"Bulunan aday çift: {len(pairs)}",
                    title="DUS Mentörü",
                )
                self.show()
                self.raise_()
                self.activateWindow()

            self.final_results = pairs
            mw.taskman.run_on_main(_on_finish)
            mw.taskman.run_on_main(lambda: self.seal_btn.setEnabled(True))
            mw.taskman.run_on_main(lambda: self.bulk_delete_btn.setEnabled(True))
            mw.taskman.run_on_main(lambda: self._display_results(self.final_results))

        except Exception as e:
            err = str(e)
            mw.taskman.run_on_main(lambda: self._show_error(err))
        finally:
            self.is_running = False

    # ── UI helpers ────────────────────────────────────────────────────────────

    def _ui(self, text, val):
        """Thread-safe progress update."""
        def _update():
            try:
                self.status_label.setText(text)
                self.progress.setValue(val)
            except (RuntimeError, AttributeError):
                pass
        mw.taskman.run_on_main(_update)

    def _show_error(self, msg):
        """Must be called on main thread."""
        try:
            QMessageBox.critical(self, "Hata", msg)
            self.start_btn.setEnabled(True)
            self.progress.setValue(0)
            self.status_label.setText("Hata oluştu. Tekrar deneyin.")
        except (RuntimeError, AttributeError):
            pass

    # ── Results ───────────────────────────────────────────────────────────────

    def _display_results(self, results):
        self.card_checkboxes = {}
        for i in reversed(range(self.content_layout.count())):
            w = self.content_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        self._load_more_btn = None
        self._all_results_to_display = results
        self._displayed_count = 0

        if not results:
            self.content_layout.addWidget(QLabel("Hiç benzer kart bulunamadı."))
        else:
            self._load_more_results()

        self.start_btn.setEnabled(True)

    def _load_more_results(self):
        start = self._displayed_count
        end = min(start + self.PAGE_SIZE, len(self._all_results_to_display))

        for item in self._all_results_to_display[start:end]:
            card_a, card_b, score = item
            self.content_layout.addWidget(self._make_pair_widget(card_a, card_b, score))

        self._displayed_count = end
        remaining = len(self._all_results_to_display) - self._displayed_count

        if remaining > 0:
            self._load_more_btn = QPushButton(f"Daha Fazla Göster ({remaining} aday daha)")
            self._load_more_btn.clicked.connect(self._on_load_more)
            self.content_layout.addWidget(self._load_more_btn)

    def _on_load_more(self):
        if self._load_more_btn:
            self._load_more_btn.setParent(None)
            self._load_more_btn = None
        self._load_more_results()

    def _make_pair_widget(self, card_a, card_b, score):
        title = f"Benzerlik: %{score * 100:.1f}"
        group = QGroupBox(title)
        
        # Color coding disabled as we no longer have LLM decisions
        border_color = "#555"

        group.setStyleSheet(
            f"QGroupBox {{ border: 2px solid {border_color}; border-radius: 5px; margin-top: 10px; font-weight: bold; }}"
        )
        layout = QHBoxLayout(group)

        for card, is_left in [(card_a, True), (card_b, False)]:
            vbox = QVBoxLayout()

            txt = QTextBrowser()
            txt.setHtml(f"<b>{card['display_question']}</b><hr>{card['display_answer']}")
            txt.setMaximumHeight(150)

            info = QLabel(f"Durum: {card['status']} | Tekrar: {card['reps']}")
            info.setStyleSheet("color: #3498db; font-size: 10px;")

            cb_select = QCheckBox("BU KARTI SİL")
            cb_select.setStyleSheet("font-weight: bold; color: #c0392b;")
            self.card_checkboxes[(card['nid'], id(group))] = cb_select

            btn = QPushButton("BU KART KALSIN")
            btn.setStyleSheet("background-color: #27ae60; color: white; padding: 5px;")

            other_nid = card_b["nid"] if is_left else card_a["nid"]
            btn.clicked.connect(lambda _, nid=other_nid: self._delete_card(nid))

            vbox.addWidget(txt)
            vbox.addWidget(info)
            vbox.addWidget(cb_select)
            vbox.addWidget(btn)
            layout.addLayout(vbox)

        return group

    def _delete_card(self, nid):
        if (
            QMessageBox.question(
                self,
                "Onay",
                "Kartı silmek istediğinize emin misiniz?\n(Bu işlem Ctrl+Z ile geri alınabilir.)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        mw.checkpoint("Smart Dedup: kart silme")
        mw.col.remNotes([nid])
        
        # Update results list: remove any pair containing this NID
        self._filter_and_refresh([nid])
        mw.reset()

    def _on_bulk_delete(self):
        to_delete = []
        for (nid, group_id), cb in self.card_checkboxes.items():
            if cb.isChecked():
                to_delete.append(nid)
        
        if not to_delete:
            QMessageBox.information(self, "Bilgi", "Lütfen silinecek kartları işaretleyin.")
            return

        if (
            QMessageBox.question(
                self,
                "Onay",
                f"{len(to_delete)} kart silinecek. Emin misiniz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        mw.checkpoint("Smart Dedup: toplu silme")
        mw.col.remNotes(to_delete)
        
        self._filter_and_refresh(to_delete)
        mw.reset()
        QMessageBox.information(self, "Başarılı", f"{len(to_delete)} kart silindi.")

    def _filter_and_refresh(self, deleted_nids):
        new_results = []
        deleted_set = set(deleted_nids)
        for item in self.final_results:
            card_a, card_b, _ = item
            
            if card_a["nid"] not in deleted_set and card_b["nid"] not in deleted_set:
                new_results.append(item)
        
        self.final_results = new_results
        self._display_results(self.final_results)

    # ── Seal & Upload ─────────────────────────────────────────────────────────

    def seal_and_upload(self):
        config = mw.addonManager.getConfig(__name__)
        pc_key = config.get("pinecone_api_key", "")
        pc_host = config.get("pinecone_index_host", "")

        if not pc_key or not pc_host:
            QMessageBox.warning(self, "Hata", "Pinecone API anahtarı veya host eksik.")
            return

        # Filter deleted notes (main thread DB access)
        survivors_cards = []
        survivors_embeddings = []
        for i, card in enumerate(self.all_cards):
            if mw.col.db.scalar(f"select id from notes where id = {card['nid']}"):
                survivors_cards.append(card)
                survivors_embeddings.append(self.all_embeddings[i])

        if not survivors_cards:
            QMessageBox.information(self, "Bilgi", "Yüklenecek kart bulunamadı.")
            return

        if (
            QMessageBox.question(
                self,
                "Onay",
                f"{len(survivors_cards)} kart Pinecone '{self.current_namespace}' namespace'ine mühürlenecek. Onaylıyor musunuz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        self.seal_btn.setEnabled(False)
        self._ui("Pinecone'a mühürleniyor...", 0)

        def _do_upload():
            try:
                self.logic.upsert_to_pinecone(
                    survivors_cards, survivors_embeddings, pc_key, pc_host, self.current_namespace
                )
                mw.taskman.run_on_main(
                    lambda: QMessageBox.information(
                        self, "Başarılı", f"'{self.current_namespace}' başarıyla mühürlendi!"
                    )
                )
                self._ui("Mühürleme tamamlandı.", 100)
            except Exception as e:
                err = str(e)
                mw.taskman.run_on_main(lambda: self._show_error(f"Upload Hatası: {err}"))
            finally:
                mw.taskman.run_on_main(lambda: self.seal_btn.setEnabled(True))

        threading.Thread(target=_do_upload, daemon=True).start()

    # ── Window lifecycle ──────────────────────────────────────────────────────

    def closeEvent(self, event):
        if self.is_running:
            self.hide()
            from aqt.utils import tooltip
            tooltip("DUS Mentörü arkaplanda çalışmaya devam ediyor...", period=3000)
            event.ignore()
        else:
            if hasattr(mw, "smart_dedup_window"):
                mw.smart_dedup_window = None
            event.accept()

    def load_config(self):
        config = mw.addonManager.getConfig(__name__)
        if not config.get("pinecone_api_key") or not config.get("pinecone_index_host"):
            QMessageBox.warning(self, "Hata", "Pinecone config eksik (API Key/Host).")
            return None
        return config

    def log(self, text):
        self.status_label.setText(text)

    def sync_from_cloud(self):
        config = self.load_config()
        if not config: return

        self.log("Pinecone'dan namespace listesi alınıyor...")
        
        # self.logic None ise geçici olarak oluştur (API anahtarı ve host config'den alınır)
        if not self.logic:
            api_key = config.get("openai_api_key", "")
            self.logic = SmartDedupLogic(api_key)
            
        ns_list = self.logic.get_pinecone_namespaces(config["pinecone_api_key"], config["pinecone_index_host"])
        
        # Orijinal isimleri gösteren bir dialog (ui.py içindeki NamespaceSelectorDialog'u ama küçük harfe zorlamayan halini kullanalım veya direkt QInputDialog)
        target_ns, ok = QInputDialog.getItem(self, "Bulut Senkronizasyonu", 
                                           "Verinin çekileceği Pinecone Namespace (Eski büyük harfli olanı seçebilirsiniz):", 
                                           ns_list, 0, False)
        
        if ok and target_ns:
            self.log(f"'{target_ns}' verileri çekiliyor ve yerel küçük harf standartına dönüştürülüyor...")
            self.sync_btn.setEnabled(False)
            
            def do_sync():
                # target_ns: Pinecone'daki gerçek isim (Örn: Protez)
                # pull_from_pinecone içinde yerel isim küçük harfe çevrilecek
                return self.logic.pull_from_pinecone(
                    target_ns, 
                    config["pinecone_api_key"], 
                    config["pinecone_index_host"],
                    progress_callback=lambda curr, total: self.progress_signal.emit(int(curr/total*100))
                )

            def on_done(count):
                self.sync_btn.setEnabled(True)
                self.progress.setValue(0)
                if isinstance(count, int):
                    QMessageBox.information(self, "Başarılı", f"{count} adet vektör yerel önbelleğe kaydedildi.")
                    self.log(f"Senkronizasyon tamam: {count} vektör.")
                else:
                    QMessageBox.critical(self, "Hata", f"Senkronizasyon hatası: {count}")

            self.worker = WorkerThread(do_sync)
            self.worker.finished.connect(on_done)
            self.worker.start()
