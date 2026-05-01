from aqt.qt import *
from aqt import mw
from .logic import SmartDedupLogic
import threading

class SmartDedupWindow(QDialog):
    def __init__(self, parent=None):
        super(SmartDedupWindow, self).__init__(parent)
        self.setWindowTitle("DUS Mentörü - Akıllı Tekilleştirme (Optimize)")
        self.setMinimumSize(900, 700)
        
        self.layout = QVBoxLayout(self)
        
        self.top_layout = QHBoxLayout()
        self.deck_combo = QComboBox()
        self.deck_combo.addItems(mw.col.decks.all_names())
        self.start_btn = QPushButton("Taramayı Başlat")
        self.start_btn.clicked.connect(self.start_process)
        self.top_layout.addWidget(QLabel("Deste:"))
        self.top_layout.addWidget(self.deck_combo)
        self.top_layout.addWidget(self.start_btn)
        self.layout.addLayout(self.top_layout)
        
        self.progress = QProgressBar()
        self.layout.addWidget(self.progress)
        self.status_label = QLabel("Başlamak için butona basın.")
        self.layout.addWidget(self.status_label)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll)

    def start_process(self):
        config = mw.addonManager.getConfig(__name__)
        api_key = config.get("openai_api_key")
        
        if not api_key or "YOUR-SK" in api_key.upper():
            QMessageBox.warning(self, "Hata", "Lütfen geçerli bir OpenAI API anahtarı girin (Config -> openai_api_key).")
            return

        self.logic = SmartDedupLogic(api_key)
        deck_name = self.deck_combo.currentText()
        self.start_btn.setEnabled(False)
        threading.Thread(target=self.process_thread, args=(deck_name,), daemon=True).start()

    def process_thread(self, deck_name):
        try:
            cards = self.logic.get_cards_from_deck(deck_name)
            self.update_ui("Vektörler OpenAI'dan alınıyor...", 20)
            
            texts = [c["text_to_vector"] for c in cards]
            embeddings = self.logic.get_embeddings(texts)
            
            self.update_ui("Benzerlik analizi yapılıyor (Bu işlem biraz sürebilir)...", 50)
            
            def progress_cb(cur, total):
                # Her 5000 adımda bir UI'yı güncelle
                percent = 50 + int((cur / total) * 45)
                self.update_ui(f"Analiz ediliyor: {cur}/{total} çift...", percent)
            
            pairs = self.logic.find_duplicates(cards, embeddings, progress_callback=progress_cb)
            
            self.update_ui(f"Tamamlandı! {len(pairs)} aday bulundu.", 100)
            mw.taskman.run_on_main(lambda: self.display_results(pairs))
        except Exception as e:
            err_msg = str(e)
            mw.taskman.run_on_main(lambda: self.show_error(err_msg))

    def update_ui(self, text, val):
        mw.taskman.run_on_main(lambda: self.status_label.setText(text))
        mw.taskman.run_on_main(lambda: self.progress.setValue(val))

    def show_error(self, msg):
        QMessageBox.critical(self, "Hata", msg)
        self.start_btn.setEnabled(True)

    def display_results(self, pairs):
        for i in reversed(range(self.content_layout.count())): 
            w = self.content_layout.itemAt(i).widget()
            if w: w.setParent(None)
        
        if not pairs:
            self.content_layout.addWidget(QLabel("Hiç benzer kart bulunamadı."))
        else:
            for card_a, card_b, score in pairs:
                self.content_layout.addWidget(self.create_pair_widget(card_a, card_b, score))
        self.start_btn.setEnabled(True)

    def create_pair_widget(self, card_a, card_b, score):
        group = QGroupBox(f"Benzerlik: %{score*100:.1f}")
        group.setStyleSheet("QGroupBox { border: 2px solid #555; border-radius: 5px; margin-top: 10px; font-weight: bold; }")
        layout = QHBoxLayout(group)
        
        for card, is_left in [(card_a, True), (card_b, False)]:
            vbox = QVBoxLayout()
            txt = QTextBrowser()
            txt.setHtml(f"<b>{card['display_question']}</b><hr>{card['display_answer']}")
            txt.setMaximumHeight(150)
            
            info = QLabel(f"Durum: {card['status']} | Tekrar: {card['reps']}")
            info.setStyleSheet("color: #3498db; font-size: 10px;")
            
            btn = QPushButton("BU KART KALSIN")
            btn.setStyleSheet("background-color: #27ae60; color: white; padding: 5px;")
            
            other_nid = card_b['nid'] if is_left else card_a['nid']
            btn.clicked.connect(lambda _, nid=other_nid, g=group: self.delete_card(nid, g))
            
            vbox.addWidget(txt)
            vbox.addWidget(info)
            vbox.addWidget(btn)
            layout.addLayout(vbox)
            
        return group

    def delete_card(self, nid, group_widget):
        if QMessageBox.question(self, 'Onay', 'Diğer kartı silmek istediğinize emin misiniz?',
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            mw.col.remNotes([nid])
            group_widget.setParent(None)
            mw.reset()
