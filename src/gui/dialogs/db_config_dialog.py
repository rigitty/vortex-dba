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
    from src.gui.workers import DbPingWorker, SchemaInitWorker
except ImportError:
    from config import get_config, update_database_config
    from gui.workers import DbPingWorker, SchemaInitWorker


from pathlib import Path
from PyQt6.QtGui import QIcon

class DbConfigDialog(QDialog):
    """Modern modal dialog for configuring and connecting to SQL Server."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SQL Server Bağlantı Yöneticisi")
        self.resize(500, 460)
        self.setModal(True)

        logo_path = Path(__file__).resolve().parent.parent.parent.parent / "logo.svg"
        if not logo_path.exists():
            logo_path = Path.cwd() / "logo.svg"
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))

        self.cfg = get_config()

        self.db_cfg = self.cfg.database

        self.ping_worker = None
        self.schema_worker = None

        self.init_ui()
        self.load_current_config()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(10)

        # Header Title
        header_box = QHBoxLayout()
        header_box.setSpacing(8)
        icon_lbl = QLabel()
        try:
            icon_lbl.setPixmap(qta.icon("fa5s.database", color="#3b82f6").pixmap(18, 18))
        except Exception:
            pass
        header_box.addWidget(icon_lbl)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(1)
        title_lbl = QLabel("SQL Server Bağlantı Yöneticisi")
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        sub_lbl = QLabel("Hedef SQL Server bağlantı parametreleri:")
        sub_lbl.setStyleSheet("font-size: 10px; color: #728499;")
        title_vbox.addWidget(title_lbl)
        title_vbox.addWidget(sub_lbl)
        header_box.addLayout(title_vbox)
        header_box.addStretch()
        main_layout.addLayout(header_box)

        # Presets Bar
        preset_lbl = QLabel("BAĞLANTI ŞABLONLARI")
        preset_lbl.setStyleSheet("font-size: 9.5px; font-weight: 700; color: #607387; letter-spacing: 0.5px;")
        main_layout.addWidget(preset_lbl)

        presets_row = QHBoxLayout()
        presets_row.setSpacing(6)
        self.btn_preset_local = QPushButton("Localhost")
        self.btn_preset_local.setToolTip("localhost:1433")
        self.btn_preset_local.clicked.connect(lambda: self.apply_preset("local"))
        presets_row.addWidget(self.btn_preset_local)

        self.btn_preset_sqlexpress = QPushButton("SQLEXPRESS")
        self.btn_preset_sqlexpress.setToolTip(".\\SQLEXPRESS yerel kurulumu")
        self.btn_preset_sqlexpress.clicked.connect(lambda: self.apply_preset("sqlexpress"))
        presets_row.addWidget(self.btn_preset_sqlexpress)

        self.btn_preset_docker = QPushButton("Docker")
        self.btn_preset_docker.setToolTip("127.0.0.1:1433 Docker container")
        self.btn_preset_docker.clicked.connect(lambda: self.apply_preset("docker"))
        presets_row.addWidget(self.btn_preset_docker)

        self.btn_preset_azure = QPushButton("Cloud / Azure")
        self.btn_preset_azure.setToolTip("Azure SQL veya Uzak SQL Server")
        self.btn_preset_azure.clicked.connect(lambda: self.apply_preset("azure"))
        presets_row.addWidget(self.btn_preset_azure)
        main_layout.addLayout(presets_row)

        # Form Fields Frame
        form_frame = QFrame()
        form_frame.setProperty("class", "card-panel")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(12, 10, 12, 10)
        form_layout.setSpacing(8)

        # Host & Port row
        host_port_row = QHBoxLayout()
        host_box = QVBoxLayout()
        host_box.setSpacing(2)
        host_lbl = QLabel("Host / IP / Instance")
        host_lbl.setStyleSheet("font-size: 10px; font-weight: 600; color: #728499;")
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("localhost veya .\\SQLEXPRESS")
        host_box.addWidget(host_lbl)
        host_box.addWidget(self.host_input)
        host_port_row.addLayout(host_box, 3)

        port_box = QVBoxLayout()
        port_box.setSpacing(2)
        port_lbl = QLabel("Port")
        port_lbl.setStyleSheet("font-size: 10px; font-weight: 600; color: #728499;")
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(1433)
        port_box.addWidget(port_lbl)
        port_box.addWidget(self.port_input)
        host_port_row.addLayout(port_box, 1)
        form_layout.addLayout(host_port_row)

        # Database Name
        db_box = QVBoxLayout()
        db_box.setSpacing(2)
        db_lbl = QLabel("Veritabanı Adı (Database)")
        db_lbl.setStyleSheet("font-size: 10px; font-weight: 600; color: #728499;")
        self.db_input = QLineEdit()
        self.db_input.setPlaceholderText("vortex_db")
        db_box.addWidget(db_lbl)
        db_box.addWidget(self.db_input)
        form_layout.addLayout(db_box)

        # User & Password row
        user_pass_row = QHBoxLayout()
        user_box = QVBoxLayout()
        user_box.setSpacing(2)
        user_lbl = QLabel("Kullanıcı (User)")
        user_lbl.setStyleSheet("font-size: 10px; font-weight: 600; color: #728499;")
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("sa")
        user_box.addWidget(user_lbl)
        user_box.addWidget(self.user_input)
        user_pass_row.addLayout(user_box, 1)

        pass_box = QVBoxLayout()
        pass_box.setSpacing(2)
        pass_lbl = QLabel("Şifre (Password)")
        pass_lbl.setStyleSheet("font-size: 10px; font-weight: 600; color: #728499;")
        
        pass_input_row = QHBoxLayout()
        pass_input_row.setSpacing(4)
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("••••••••")
        pass_input_row.addWidget(self.pass_input)

        self.btn_toggle_pw = QPushButton()
        self.btn_toggle_pw.setFixedWidth(30)
        self.btn_toggle_pw.setFixedHeight(24)
        try:
            self.btn_toggle_pw.setIcon(qta.icon("fa5s.eye", color="#8294a8"))
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
        self.diag_box.setStyleSheet("background-color: #05080e; border: 1px solid #141f2e; border-radius: 5px; padding: 6px;")
        diag_layout = QVBoxLayout(self.diag_box)
        diag_layout.setContentsMargins(8, 6, 8, 6)
        self.diag_lbl = QLabel("Sunucu bağlantısını test edebilir veya ayarları kaydedip bağlanabilirsiniz.")
        self.diag_lbl.setStyleSheet("font-size: 10px; color: #728499; font-family: 'JetBrains Mono', monospace;")
        self.diag_lbl.setWordWrap(True)
        diag_layout.addWidget(self.diag_lbl)
        main_layout.addWidget(self.diag_box)

        # Actions Toolbar
        actions_row = QHBoxLayout()
        actions_row.setSpacing(6)
        
        self.btn_schema = QPushButton("Şemayı Kur")
        self.btn_schema.setToolTip("01_schema.sql ile tabloları ve temel indeksleri oluşturur")
        self.btn_schema.clicked.connect(self.init_schema)
        actions_row.addWidget(self.btn_schema)

        actions_row.addStretch()

        self.btn_test = QPushButton("Bağlantıyı Test Et")
        self.btn_test.clicked.connect(self.test_connection)
        actions_row.addWidget(self.btn_test)

        self.btn_save_connect = QPushButton("Bağlan & Kaydet")
        self.btn_save_connect.setProperty("class", "btn-primary")
        self.btn_save_connect.clicked.connect(self.save_and_connect)
        actions_row.addWidget(self.btn_save_connect)

        main_layout.addLayout(actions_row)


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
        elif preset_type == "sqlexpress":
            self.host_input.setText(".\\SQLEXPRESS")
            self.port_input.setValue(1433)
            self.db_input.setText("vortex_db")
            self.user_input.setText("sa")
            self.pass_input.setText("")
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
            password=self.pass_input.text(),
            timeout=3,
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
            tbl_count = res.get("table_count", 0)
            self.diag_lbl.setText(f"✔ BAĞLANTI BAŞARILI ({latency} ms ping)\n{ver}\nHedef DB: [{db}] | Tablo Sayısı: {tbl_count}")
            self.diag_lbl.setStyleSheet("color: #34d399; font-weight: 700;")
        else:
            err = res.get("error", "Bilinmeyen hata")
            self.diag_lbl.setText(f"❌ BAĞLANTI BAŞARISIZ: {err}")
            self.diag_lbl.setStyleSheet("color: #f87171; font-weight: 700;")

    def init_schema(self):
        # First save current config so connection uses entered credentials
        self.apply_inputs_to_config()
        self.btn_schema.setEnabled(False)
        self.btn_schema.setText("⏳ Şema Kuruluyor...")

        self.schema_worker = SchemaInitWorker()
        self.schema_worker.finished_signal.connect(self.on_schema_finished)
        self.schema_worker.start()

    def on_schema_finished(self, success: bool, msg: str):
        self.btn_schema.setEnabled(True)
        self.btn_schema.setText("📋 Şemayı Kur (01_schema.sql)")
        if success:
            QMessageBox.information(self, "Şema Kuruldu", msg)
            self.diag_lbl.setText(f"✔ {msg}")
            self.diag_lbl.setStyleSheet("color: #34d399; font-weight: 700;")
        else:
            QMessageBox.warning(self, "Şema Kurulum Hatası", msg)
            self.diag_lbl.setText(f"❌ {msg}")
            self.diag_lbl.setStyleSheet("color: #f87171; font-weight: 700;")

    def apply_inputs_to_config(self):
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

    def save_and_connect(self):
        self.apply_inputs_to_config()
        self.accept()

