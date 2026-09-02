"""SQL Server Connection Manager Dialog for PyQt6."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QPushButton,
    QFrame,
    QMessageBox,
)
from PyQt6.QtCore import Qt
import qtawesome as qta

try:
    from src.config import get_config, update_database_config
    from src.gui.workers import DbPingWorker
except ImportError:
    from config import get_config, update_database_config
    from gui.workers import DbPingWorker


class DbConfigDialog(QDialog):
    """Modern modal dialog for configuring SQL Server connection settings."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SQL Server Bağlantı Yöneticisi")
        self.resize(520, 480)
        self.setModal(True)

        self.cfg = get_config()
        self.db_cfg = self.cfg.database

        self.ping_worker = None

        self.init_ui()
        self.load_current_config()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Header Title
        header_box = QHBoxLayout()
        icon_lbl = QLabel()
        try:
            icon_lbl.setPixmap(qta.icon("fa5s.database", color="#38bdf8").pixmap(24, 24))
        except Exception:
            pass
        header_box.addWidget(icon_lbl)

        title_vbox = QVBoxLayout()
        title_lbl = QLabel("SQL Server Bağlantı Yöneticisi")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        sub_lbl = QLabel("İzlenecek ve optimize edilecek hedef veritabanı")
        sub_lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")
        title_vbox.addWidget(title_lbl)
        title_vbox.addWidget(sub_lbl)
        header_box.addLayout(title_vbox)
        header_box.addStretch()
        main_layout.addLayout(header_box)

        # Presets Bar
        preset_lbl = QLabel("HIZLI ŞABLONLAR (PRESETS)")
        preset_lbl.setStyleSheet("font-size: 10.5px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")
        main_layout.addWidget(preset_lbl)

        presets_row = QHBoxLayout()
        self.btn_preset_local = QPushButton("⚡ Localhost (1433)")
        self.btn_preset_local.clicked.connect(lambda: self.apply_preset("local"))
        presets_row.addWidget(self.btn_preset_local)

        self.btn_preset_docker = QPushButton("🐳 Docker Container")
        self.btn_preset_docker.clicked.connect(lambda: self.apply_preset("docker"))
        presets_row.addWidget(self.btn_preset_docker)

        self.btn_preset_azure = QPushButton("☁️ Azure SQL / Cloud")
        self.btn_preset_azure.clicked.connect(lambda: self.apply_preset("azure"))
        presets_row.addWidget(self.btn_preset_azure)
        main_layout.addLayout(presets_row)

        # Form Fields Frame
        form_frame = QFrame()
        form_frame.setProperty("class", "card-panel")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(16, 14, 16, 14)
        form_layout.setSpacing(12)

        # Host & Port row
        host_port_row = QHBoxLayout()
        host_box = QVBoxLayout()
        host_lbl = QLabel("Host / IP Adresi")
        host_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("localhost")
        host_box.addWidget(host_lbl)
        host_box.addWidget(self.host_input)
        host_port_row.addLayout(host_box, 3)

        port_box = QVBoxLayout()
        port_lbl = QLabel("Port")
        port_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(1433)
        port_box.addWidget(port_lbl)
        port_box.addWidget(self.port_input)
        host_port_row.addLayout(port_box, 1)
        form_layout.addLayout(host_port_row)

        # Database Name
        db_box = QVBoxLayout()
        db_lbl = QLabel("Veritabanı Adı (Database Name)")
        db_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")
        self.db_input = QLineEdit()
        self.db_input.setPlaceholderText("vortex_db")
        db_box.addWidget(db_lbl)
        db_box.addWidget(self.db_input)
        form_layout.addLayout(db_box)

        # User & Password row
        user_pass_row = QHBoxLayout()
        user_box = QVBoxLayout()
        user_lbl = QLabel("Kullanıcı Adı (User)")
        user_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("sa")
        user_box.addWidget(user_lbl)
        user_box.addWidget(self.user_input)
        user_pass_row.addLayout(user_box, 1)

        pass_box = QVBoxLayout()
        pass_lbl = QLabel("Şifre (Password)")
        pass_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")
        
        pass_input_row = QHBoxLayout()
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("••••••••")
        pass_input_row.addWidget(self.pass_input)

        self.btn_toggle_pw = QPushButton()
        self.btn_toggle_pw.setFixedWidth(36)
        try:
            self.btn_toggle_pw.setIcon(qta.icon("fa5s.eye", color="#94a3b8"))
        except Exception:
            self.btn_toggle_pw.setText("👁")
        self.btn_toggle_pw.clicked.connect(self.toggle_password)
        pass_input_row.addWidget(self.btn_toggle_pw)

        pass_box.addWidget(pass_lbl)
        pass_box.addLayout(pass_input_row)
        user_pass_row.addLayout(pass_box, 1)
        form_layout.addLayout(user_pass_row)

        main_layout.addWidget(form_frame)

        # Diagnostic Box
        self.diag_box = QFrame()
        self.diag_box.setStyleSheet("background-color: #060911; border: 1px solid #1e293b; border-radius: 8px; padding: 8px;")
        diag_layout = QVBoxLayout(self.diag_box)
        diag_layout.setContentsMargins(10, 8, 10, 8)
        self.diag_lbl = QLabel("Bağlantı durumunu test etmek için aşağıdaki butona basın.")
        self.diag_lbl.setStyleSheet("font-size: 11px; color: #64748b; font-family: 'JetBrains Mono', monospace;")
        self.diag_lbl.setWordWrap(True)
        diag_layout.addWidget(self.diag_lbl)
        main_layout.addWidget(self.diag_box)

        # Footer Actions
        footer_row = QHBoxLayout()
        self.btn_reset = QPushButton("Varsayılana Sıfırla")
        self.btn_reset.setStyleSheet("color: #64748b; border: none; font-size: 11px;")
        self.btn_reset.clicked.connect(lambda: self.apply_preset("local"))
        footer_row.addWidget(self.btn_reset)
        footer_row.addStretch()

        self.btn_test = QPushButton("⚡ Bağlantıyı Test Et")
        self.btn_test.clicked.connect(self.test_connection)
        footer_row.addWidget(self.btn_test)

        self.btn_save = QPushButton("💾 Kaydet & Aktif Et")
        self.btn_save.setProperty("class", "btn-success")
        self.btn_save.clicked.connect(self.save_and_close)
        footer_row.addWidget(self.btn_save)

        main_layout.addLayout(footer_row)

    def load_current_config(self):
        self.host_input.setText(self.db_cfg.host)
        self.port_input.setValue(self.db_cfg.port)
        self.db_input.setText(self.db_cfg.dbname)
        self.user_input.setText(self.db_cfg.user)
        self.pass_input.setText(self.db_cfg.password)

    def toggle_password(self):
        if self.pass_input.echoMode() == QLineEdit.EchoMode.Password:
            self.pass_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)

    def apply_preset(self, preset_type: str):
        if preset_type == "local":
            self.host_input.setText("localhost")
            self.port_input.setValue(1433)
            self.db_input.setText("vortex_db")
            self.user_input.setText("sa")
            self.pass_input.setText("VortexPassword123!")
        elif preset_type == "docker":
            self.host_input.setText("127.0.0.1")
            self.port_input.setValue(1433)
            self.db_input.setText("vortex_db")
            self.user_input.setText("sa")
            self.pass_input.setText("VortexPassword123!")
        elif preset_type == "azure":
            self.host_input.setText("vortex-sql.database.windows.net")
            self.port_input.setValue(1433)
            self.db_input.setText("production_db")
            self.user_input.setText("vortex_admin")
            self.pass_input.setText("")

    def test_connection(self):
        self.btn_test.setEnabled(False)
        self.btn_test.setText("⏳ Test Ediliyor...")
        self.diag_lbl.setText("SQL Server'a bağlanılıyor...")
        self.diag_lbl.setStyleSheet("color: #38bdf8;")

        self.ping_worker = DbPingWorker(
            host=self.host_input.text().strip(),
            port=self.port_input.value(),
            dbname=self.db_input.text().strip(),
            user=self.user_input.text().strip(),
            password=self.pass_input.text()
        )
        self.ping_worker.result_signal.connect(self.on_ping_result)
        self.ping_worker.start()

    def on_ping_result(self, res: dict):
        self.btn_test.setEnabled(True)
        self.btn_test.setText("⚡ Bağlantıyı Test Et")

        if res.get("success"):
            latency = res.get("latency_ms", 0)
            ver = res.get("server_version", "SQL Server")
            db = res.get("database", "vortex_db")
            self.diag_lbl.setText(f"✔ BAĞLANTI BAŞARILI ({latency} ms ping)\n{ver}\nHedef DB: [{db}]")
            self.diag_lbl.setStyleSheet("color: #34d399; font-weight: 700;")
        else:
            err = res.get("error", "Bilinmeyen hata")
            self.diag_lbl.setText(f"❌ BAĞLANTI BAŞARISIZ: {err}")
            self.diag_lbl.setStyleSheet("color: #f87171; font-weight: 700;")

    def save_and_close(self):
        host = self.host_input.text().strip()
        port = self.port_input.value()
        dbname = self.db_input.text().strip()
        user = self.user_input.text().strip()
        password = self.pass_input.text()

        update_database_config(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        QMessageBox.information(self, "Başarılı", f"SQL Server bağlantı ayarları güncellendi:\n{host}:{port} [{dbname}]")
        self.accept()
