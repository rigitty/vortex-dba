"""Enterprise Internationalization (i18n) and Localization Engine for VortexDBA.

Provides centralized English (default) and Turkish translation dictionaries,
parameterized formatting, dynamic language switching, and persistence.
"""
from typing import Any
try:
    from src.config import get_config, update_language
except ImportError:
    from config import get_config, update_language



_ACTIVE_LANG = "en"

TRANSLATIONS: dict[str, dict[str, str]] = {
    # -------------------------------------------------------------------------
    # NAVIGATION & TOP BAR
    # -------------------------------------------------------------------------
    "nav.server": {
        "en": "SERVER",
        "tr": "SUNUCU"
    },
    "nav.sql": {
        "en": "SQL",
        "tr": "SQL"
    },
    "nav.queries": {
        "en": "QUERIES",
        "tr": "SORGULAR"
    },
    "nav.index": {
        "en": "INDEX",
        "tr": "İNDEKS"
    },
    "nav.management": {
        "en": "MANAGEMENT",
        "tr": "YÖNETİM"
    },
    "header.brand_sub": {
        "en": "AUTONOMOUS MSSQL TUNER",
        "tr": "OTONOM MSSQL OPTİMİZATÖRÜ"
    },
    "header.engine_active": {
        "en": "● AUTONOMOUS: ACTIVE (24/7)",
        "tr": "● OTONOM: AKTİF (7/24)"
    },
    "header.engine_inactive": {
        "en": "○ AUTONOMOUS: OFF",
        "tr": "○ OTONOM: KAPALI"
    },
    "header.engine_tip": {
        "en": "Toggle 24/7 Autonomous DMV Optimization Engine (Click to start/pause)",
        "tr": "7/24 Otonom DMV Optimizasyon Motoru (Başlatmak/Durdurmak için tıklayın)"
    },
    "header.health_online": {
        "en": "ONLINE",
        "tr": "ONLINE"
    },
    "header.health_offline": {
        "en": "OFFLINE | NO CONNECTION",
        "tr": "OFFLINE | BAĞLANTI YOK"
    },
    "header.theme_tip": {
        "en": "Switch Dark / Light Theme",
        "tr": "Karanlık / Aydınlık Tema Değiştir"
    },
    "header.lang_tip": {
        "en": "Switch Language (EN / TR)",
        "tr": "Dili Değiştir (EN / TR)"
    },
    "header.win_min": {
        "en": "Minimize",
        "tr": "Simge Durumuna Küçült"
    },
    "header.win_max": {
        "en": "Maximize / Restore",
        "tr": "Ekranı Kapla / Geri Yükle"
    },
    "header.win_close": {
        "en": "Close",
        "tr": "Kapat"
    },

    # -------------------------------------------------------------------------
    # PAGE 0: SERVER CONNECTION
    # -------------------------------------------------------------------------
    "connect.target_conn_title": {
        "en": "TARGET SQL SERVER CONNECTION PARAMETERS",
        "tr": "HEDEF SQL SERVER BAĞLANTI PARAMETRELERİ"
    },
    "connect.target_conn_desc": {
        "en": "Enter Microsoft SQL Server TDS connection parameters for VortexDBA autonomous indexing engine:",
        "tr": "VortexDBA otonom optimizasyon motorunun bağlanacağı Microsoft SQL Server TDS bağlantı ayarlarını girin:"
    },
    "connect.host": {
        "en": "Host / IP:",
        "tr": "Host / IP:"
    },
    "connect.port": {
        "en": "Port:",
        "tr": "Port:"
    },
    "connect.dbname": {
        "en": "Database Name:",
        "tr": "Veritabanı Adı:"
    },
    "connect.user": {
        "en": "Username:",
        "tr": "Kullanıcı Adı:"
    },
    "connect.pass": {
        "en": "Password:",
        "tr": "Şifre:"
    },
    "connect.quick_presets": {
        "en": "QUICK CONNECTION PRESETS:",
        "tr": "HIZLI BAĞLANTI ŞABLONLARI:"
    },
    "connect.preset_docker": {
        "en": "Local Docker MSSQL (localhost:1433)",
        "tr": "Yerel Docker MSSQL (localhost:1433)"
    },
    "connect.preset_master": {
        "en": "Master DB (127.0.0.1:1433)",
        "tr": "Master DB (127.0.0.1:1433)"
    },
    "connect.btn_test": {
        "en": "TEST CONNECTION",
        "tr": "BAĞLANTIYI TEST ET"
    },
    "connect.btn_save": {
        "en": "SAVE & CONNECT TO SERVER",
        "tr": "KAYDET & SUNUCUYA BAĞLAN"
    },
    "connect.testing": {
        "en": "Connecting to server...",
        "tr": "Sunucuya bağlanılıyor..."
    },
    "connect.test_success": {
        "en": "CONNECTION SUCCESSFUL!",
        "tr": "BAĞLANTI BAŞARILI!"
    },
    "connect.test_target_db": {
        "en": "Target DB:",
        "tr": "Hedef DB:"
    },
    "connect.test_error": {
        "en": "CONNECTION ERROR:",
        "tr": "BAĞLANTI HATASI:"
    },
    "connect.save_success": {
        "en": "Connection parameters successfully saved and activated!",
        "tr": "Bağlantı parametreleri başarıyla kaydedildi ve aktif edildi!"
    },
    "connect.live_server_title": {
        "en": "LIVE SERVER STATUS & TABLES",
        "tr": "CANLI SUNUCU DURUMU & TABLOLAR"
    },
    "connect.state_checking": {
        "en": "Checking connection status...",
        "tr": "Bağlantı durumu kontrol ediliyor..."
    },
    "connect.state_connected": {
        "en": "Connected (Live Traffic Active)",
        "tr": "Bağlantı Aktif (Canlı Trafik Dinleniyor)"
    },
    "connect.state_disconnected": {
        "en": "No Connection - Showing Cached Data",
        "tr": "Bağlantı Yok - Önbellek Gösteriliyor"
    },
    "connect.tables_section": {
        "en": "DATABASE TABLES & ROW COUNTS:",
        "tr": "VERİTABANINDAKİ TABLOLAR & SATIR SAYILARI:"
    },
    "connect.tbl_col_name": {
        "en": "Table Name",
        "tr": "Tablo Adı"
    },
    "connect.tbl_col_rows": {
        "en": "Row Count",
        "tr": "Satır Sayısı"
    },
    "connect.tbl_col_scan": {
        "en": "Table Scan",
        "tr": "Table Scan"
    },
    "connect.tbl_col_seek": {
        "en": "Index Seek",
        "tr": "Index Seek"
    },
    "connect.btn_to_editor": {
        "en": "Go to SQL Editor ➔",
        "tr": "SQL Editörüne Geç ➔"
    },
    "connect.btn_to_queries": {
        "en": "Inspect Queries ➔",
        "tr": "Sorguları İncele ➔"
    },

    # -------------------------------------------------------------------------
    # PAGE 1: SQL EDITOR
    # -------------------------------------------------------------------------
    "editor.title": {
        "en": "INTERACTIVE T-SQL EDITOR & LIVE INDEX ANALYSIS",
        "tr": "İNTERAKTİF T-SQL EDİTÖRÜ & CANLI İNDEKS ANALİZİ"
    },
    "editor.btn_clear": {
        "en": "Clear",
        "tr": "Temizle"
    },
    "editor.btn_run": {
        "en": "RUN QUERY (Ctrl+Enter)",
        "tr": "SORGUYU ÇALIŞTIR (Ctrl+Enter)"
    },
    "editor.sample_queries": {
        "en": "QUICK TEST QUERIES:",
        "tr": "HIZLI TEST SORGULARI:"
    },
    "editor.sample_p1": {
        "en": "Order Revenue Report (Heavy Full Scan)",
        "tr": "Sipariş Ciro Raporu (Ağır Full Scan)"
    },
    "editor.sample_p2": {
        "en": "Date Ordered Orders (Sort + Scan)",
        "tr": "Tarih Sıralı Siparişler (Sort + Scan)"
    },
    "editor.sample_p3": {
        "en": "City-Based Spending (JOIN Scan)",
        "tr": "Şehir Bazlı Harcama (JOIN Scan)"
    },
    "editor.sample_p4": {
        "en": "Email LIKE Search",
        "tr": "E-Posta LIKE Arama"
    },
    "editor.stats_exec_time": {
        "en": "EXECUTION TIME:",
        "tr": "YÜRÜTME SÜRESİ:"
    },
    "editor.stats_returned_rows": {
        "en": "RETURNED ROWS:",
        "tr": "DÖNEN SATIR:"
    },
    "editor.stats_columns": {
        "en": "COLUMNS:",
        "tr": "SÜTUN SAYISI:"
    },
    "editor.rec_found": {
        "en": "INDEX RECOMMENDATION FOUND",
        "tr": "DİNAMİK İNDEKS ÖNERİSİ BULUNDU"
    },
    "editor.rec_btn": {
        "en": "RUN & APPLY RECOMMENDATION TO SQL SERVER",
        "tr": "ÖNERİYİ SQL SERVER'DA ÇALIŞTIR & UYGULA"
    },
    "editor.no_sql": {
        "en": "Please enter a SQL query to execute.",
        "tr": "Lütfen çalıştırılacak bir SQL sorgusu yazın."
    },
    "editor.executing": {
        "en": "Executing query...",
        "tr": "Sorgu çalıştırılıyor..."
    },
    "editor.success_msg": {
        "en": "Query executed successfully!",
        "tr": "Sorgu başarıyla çalıştırıldı!"
    },

    # -------------------------------------------------------------------------
    # PAGE 2: CAPTURED QUERIES
    # -------------------------------------------------------------------------
    "queries.title": {
        "en": "ALL CAPTURED & EXECUTED QUERIES",
        "tr": "YAKALANAN VE ÇALIŞTIRILAN TÜM SORGULAR"
    },
    "queries.btn_refresh": {
        "en": "🔄 REFRESH",
        "tr": "🔄 YENİLE"
    },
    "queries.btn_select_all": {
        "en": "SELECT / DESELECT ALL",
        "tr": "TÜMÜNÜ SEÇ / BIRAK"
    },
    "queries.btn_delete_selected": {
        "en": "DELETE SELECTED",
        "tr": "SEÇİLENLERİ SİL"
    },
    "queries.btn_clear_all": {
        "en": "CLEAR ALL QUERIES",
        "tr": "TÜM SORGULARI TEMİZLE"
    },
    "queries.col_select": {
        "en": "SELECT",
        "tr": "SEÇ"
    },
    "queries.col_title": {
        "en": "QUERY NAME & TABLE",
        "tr": "SORGU ADI & TABLO"
    },
    "queries.col_sql": {
        "en": "SQL QUERY",
        "tr": "SQL SORGUSU"
    },
    "queries.col_status": {
        "en": "INDEX STATUS",
        "tr": "İNDEKS DURUMU"
    },
    "queries.col_time": {
        "en": "TIMESTAMP",
        "tr": "YAZILMA / YAKALANMA ZAMANI"
    },
    "queries.col_dur": {
        "en": "DURATION (ms)",
        "tr": "SÜRE (ms)"
    },
    "queries.status_applied": {
        "en": "[INDEX APPLIED]",
        "tr": "[İNDEKS UYGULANDI]"
    },
    "queries.status_no_index": {
        "en": "[No Index]",
        "tr": "[İndekssiz]"
    },

    # -------------------------------------------------------------------------
    # PAGE 3: INDEX MANAGEMENT
    # -------------------------------------------------------------------------
    "index.batch_ops": {
        "en": "BATCH INDEX OPERATIONS:",
        "tr": "TOPLU İNDEKS OPERASYONLARI:"
    },
    "index.btn_apply_all": {
        "en": "APPLY ALL AUTOMATICALLY",
        "tr": "TÜM HEPSİNİ OTOMATİK UYGULA"
    },
    "index.btn_benchmark_all": {
        "en": "BENCHMARK ALL",
        "tr": "TÜM HEPSİNİ BENCHMARK ET"
    },
    "index.btn_reset": {
        "en": "RESET INDEXES",
        "tr": "İNDEKSLERİ SIFIRLA"
    },
    "index.table1_title": {
        "en": "QUERIES AND MATCHED INDEX NUMBERS",
        "tr": "SORGULAR VE EŞLEŞEN İNDEKS NUMARALARI"
    },
    "index.t1_col_query": {
        "en": "SYSTEM QUERY & TABLE",
        "tr": "SİSTEM SORGUSU & TABLO"
    },
    "index.t1_col_sql": {
        "en": "SQL QUERY (SUMMARY)",
        "tr": "SQL SORGUSU (ÖZET)"
    },
    "index.t1_col_match": {
        "en": "MATCHED INDEX",
        "tr": "EŞLEŞEN İNDEKS"
    },
    "index.t1_col_before": {
        "en": "BEFORE INDEX (ms)",
        "tr": "İNDEKS ÖNCESİ (ms)"
    },
    "index.t1_col_after": {
        "en": "AFTER INDEX (ms)",
        "tr": "İNDEKS SONRASI (ms)"
    },
    "index.t1_col_speedup": {
        "en": "SPEEDUP RATIO",
        "tr": "HIZLANMA ORANI"
    },
    "index.t1_col_actions": {
        "en": "ACTIONS & TEST",
        "tr": "İŞLEMLER & TEST"
    },
    "index.btn_apply": {
        "en": "Index",
        "tr": "İndeksle"
    },
    "index.btn_test": {
        "en": "Test",
        "tr": "Test"
    },
    "index.btn_delete": {
        "en": "Delete",
        "tr": "Sil"
    },
    "index.table2_title": {
        "en": "NUMBERED INDEX CATALOG & SQL SERVER STATUS",
        "tr": "NUMARALANDIRILMIŞ İNDEKS KATALOĞU & SQL SERVER DURUMU"
    },
    "index.t2_col_no": {
        "en": "INDEX NO",
        "tr": "İNDEKS NO"
    },
    "index.t2_col_name": {
        "en": "INDEX NAME & TABLE",
        "tr": "İNDEKS ADI & TABLO"
    },
    "index.t2_col_status": {
        "en": "STATUS",
        "tr": "DURUM"
    },
    "index.t2_col_ddl": {
        "en": "COLUMNS & DDL",
        "tr": "KOLONLAR & DDL"
    },
    "index.t2_col_queries": {
        "en": "QUERIES USING THIS INDEX",
        "tr": "BU İNDEKSİ KULLANAN SORGULAR"
    },
    "index.t2_col_actions": {
        "en": "ACTIONS",
        "tr": "İŞLEMLER"
    },
    "index.btn_create_idx": {
        "en": "Create Index",
        "tr": "İndeksi Oluştur"
    },
    "index.btn_drop_idx": {
        "en": "Drop Index",
        "tr": "İndeksi Kaldır"
    },
    "index.status_active": {
        "en": "● Active (SQL Server)",
        "tr": "● Aktif (SQL Server)"
    },
    "index.status_rec": {
        "en": "○ Recommended",
        "tr": "○ Önerilen"
    },

    # -------------------------------------------------------------------------
    # SPLASH SCREEN
    # -------------------------------------------------------------------------
    "splash.step1": {
        "en": "● Scanning SQL Server connection lines...",
        "tr": "● SQL Server bağlantı hatları taranıyor..."
    },
    "splash.step2": {
        "en": "● Loading autonomous AI optimization engine...",
        "tr": "● Otonom AI optimizasyon motoru yükleniyor..."
    },
    "splash.step3": {
        "en": "● Live telemetry & DBA control panel ready...",
        "tr": "● Canlı telemetri ve DBA kontrol paneli hazır..."
    },
    "splash.ready": {
        "en": "✔ VortexDBA ready.",
        "tr": "✔ VortexDBA hazır."
    },

    # -------------------------------------------------------------------------
    # PAGE 0: SERVER CONNECTION
    # -------------------------------------------------------------------------
    "connect.show_pass": {
        "en": "Show Password",
        "tr": "Şifreyi Göster"
    },
    "connect.hide_pass": {
        "en": "Hide Password",
        "tr": "Şifreyi Gizle"
    },

    # -------------------------------------------------------------------------
    # PAGE 4: MANAGEMENT & AUTONOMOUS ENGINE
    # -------------------------------------------------------------------------
    "mgmt.control_title": {
        "en": "AUTONOMOUS DBA ENGINE CONTROL & OPERATION MODE",
        "tr": "OTONOM DBA MOTOR KONTROLÜ & ÇALIŞMA MODU"
    },
    "mgmt.engine_ctrl_title": {
        "en": "AUTONOMOUS ENGINE CONTROL:",
        "tr": "OTONOM MOTOR KONTROLÜ:"
    },
    "mgmt.btn_engine_active": {
        "en": "● AUTONOMOUS ENGINE: ACTIVE (24/7)",
        "tr": "● OTONOM MOTOR: AKTİF (7/24)"
    },
    "mgmt.btn_engine_inactive": {
        "en": "○ AUTONOMOUS ENGINE: OFF",
        "tr": "○ OTONOM MOTOR: KAPALI"
    },
    "mgmt.last_action_title": {
        "en": "LATEST INDEX APPLICATION:",
        "tr": "EN SON YAPILAN İNDEKS UYGULAMASI:"
    },
    "mgmt.last_action_none": {
        "en": "No custom index applied yet.",
        "tr": "Henüz özel indeks uygulanmadı."
    },
    "mgmt.quota_title": {
        "en": "AUTONOMOUS QUOTA & SAFETY SETTING:",
        "tr": "OTONOM KOTA & GÜVENLİK AYARI:"
    },
    "mgmt.quota_label": {
        "en": "Max Index Quota:",
        "tr": "Max İndeks Kotası:"
    },
    "mgmt.safety_strip": {
        "en": "✔ ONLINE=ON | ✔ 15% Circuit Breaker | ✔ Dynamic Balancing",
        "tr": "✔ ONLINE=ON | ✔ %15 Devre Kesici | ✔ Dinamik Dengeleme"
    },
    "mgmt.stat_custom_title": {
        "en": "APPLIED CUSTOM INDEXES",
        "tr": "UYGULANAN ÖZEL İNDEKSLER"
    },
    "mgmt.stat_custom_val": {
        "en": "{count} Active",
        "tr": "{count} Aktif"
    },
    "mgmt.stat_custom_sub": {
        "en": "{count} DDL Active on Server",
        "tr": "{count} adet DDL devrede"
    },
    "mgmt.stat_queries_title": {
        "en": "CAPTURED QUERIES",
        "tr": "YAKALANAN SORGULAR"
    },
    "mgmt.stat_queries_val": {
        "en": "{count} Queries",
        "tr": "{count} Sorgu"
    },
    "mgmt.stat_queries_sub": {
        "en": "DMV + Live Analysis",
        "tr": "DMV + Canlı Analiz"
    },
    "mgmt.stat_speedup_title": {
        "en": "AVERAGE SPEEDUP GAIN",
        "tr": "GENEL ORTALAMA HIZ KAZANCI"
    },
    "mgmt.stat_speedup_none_val": {
        "en": "0.0x (+0%)",
        "tr": "0.0x (+%0)"
    },
    "mgmt.stat_speedup_none_sub": {
        "en": "No index / benchmarks yet",
        "tr": "Henüz indeks/ölçüm yok"
    },
    "mgmt.stat_speedup_active_val": {
        "en": "16.4x (+94.2%)",
        "tr": "16.4x (+%94.2)"
    },
    "mgmt.stat_speedup_active_sub": {
        "en": "Accelerated with {count} active indexes",
        "tr": "{count} aktif indeks ile hızlandı"
    },
    "mgmt.stat_engine_title": {
        "en": "AUTONOMOUS ENGINE STATUS",
        "tr": "OTONOM MOTOR DURUMU"
    },
    "mgmt.stat_engine_active_val": {
        "en": "ACTIVE 24/7",
        "tr": "7/24 AKTİF"
    },
    "mgmt.stat_engine_active_sub": {
        "en": "Live DMV Listening On",
        "tr": "Canlı DMV Dinleme Açık"
    },
    "mgmt.stat_engine_stopped_val": {
        "en": "STOPPED",
        "tr": "DURDURULDU"
    },
    "mgmt.stat_engine_stopped_sub": {
        "en": "Manual Mode (Listening Paused)",
        "tr": "Manuel Mod (Dinleme Kapalı)"
    },
    "mgmt.stat_engine_status": {
        "en": "ENGINE STATUS",
        "tr": "MOTOR DURUMU"
    },
    "mgmt.stat_engine_active": {
        "en": "ACTIVE 24/7",
        "tr": "7/24 AKTİF"
    },
    "mgmt.stat_engine_stopped": {
        "en": "STOPPED",
        "tr": "DURDURULDU"
    },
    "mgmt.stat_mode": {
        "en": "CURRENT MODE",
        "tr": "MEVCUT ÇALIŞMA MODU"
    },
    "mgmt.mode_auto": {
        "en": "Autonomous (Auto Apply)",
        "tr": "Otonom (Otomatik Uygulama)"
    },
    "mgmt.mode_advisor": {
        "en": "Advisor (Approval Required)",
        "tr": "Danışman (Onay Bekler)"
    },
    "mgmt.stat_applied_indexes": {
        "en": "APPLIED INDEXES",
        "tr": "UYGULANAN İNDEKS"
    },
    "mgmt.stat_gain": {
        "en": "TOTAL PERFORMANCE GAIN",
        "tr": "TOPLAM PERFORMANS KAZANCI"
    },
    "mgmt.gain_faster": {
        "en": "{gain}x Faster",
        "tr": "{gain}x Daha Hızlı"
    },
    "mgmt.btn_engine_on": {
        "en": "● AUTONOMOUS ENGINE: ACTIVE (24/7)",
        "tr": "● OTONOM MOTOR: AKTİF (7/24)"
    },
    "mgmt.btn_engine_off": {
        "en": "○ AUTONOMOUS ENGINE: OFF",
        "tr": "○ OTONOM MOTOR: KAPALI"
    },
    "mgmt.opt_mode_lbl": {
        "en": "Operating Mode:",
        "tr": "Çalışma Modu:"
    },
    "mgmt.opt_advisor": {
        "en": "Advisor Mode (Recommendations only, manual approval)",
        "tr": "Danışman Modu (Sadece öneri üretir, onay bekler)"
    },
    "mgmt.opt_auto": {
        "en": "Autonomous Mode (Automatic index creation & validation)",
        "tr": "Otonom Modu (Otomatik indeks oluşturur ve doğrular)"
    },
    "mgmt.btn_save_mode": {
        "en": "SAVE MODE",
        "tr": "MODU KAYDET"
    },
    "mgmt.audit_title": {
        "en": "AUTONOMOUS DECISION HISTORY (AUDIT TRAIL):",
        "tr": "OTONOM KARAR GEÇMİŞİ (AUDIT TRAIL):"
    },
    "mgmt.btn_clear_audit": {
        "en": "🧹 Clear Audit History",
        "tr": "🧹 Karar Geçmişini Temizle"
    },
    "mgmt.audit_col_type": {
        "en": "Action Type",
        "tr": "İşlem Türü"
    },
    "mgmt.audit_col_details": {
        "en": "Details",
        "tr": "Ayrıntı"
    },
    "mgmt.audit_col_time": {
        "en": "Timestamp",
        "tr": "Zaman"
    },
    "mgmt.telemetry_title": {
        "en": "STREAM TELEMETRY LOGS:",
        "tr": "STREAM TELEMETRY LOGS:"
    },

    # -------------------------------------------------------------------------
    # TOAST NOTIFICATIONS & DIALOGS
    # -------------------------------------------------------------------------
    "toast.engine_active_title": {
        "en": "AUTONOMOUS ENGINE ACTIVE",
        "tr": "OTONOM MOTOR AKTİF"
    },
    "toast.engine_active_msg": {
        "en": "24/7 Live DMV listening and auto optimization enabled.",
        "tr": "7/24 Canlı DMV dinleme ve otomatik optimizasyon devrede."
    },
    "toast.engine_stopped_title": {
        "en": "AUTONOMOUS ENGINE STOPPED",
        "tr": "OTONOM MOTOR DURDURULDU"
    },
    "toast.engine_stopped_msg": {
        "en": "Auto optimization paused (Manual Mode).",
        "tr": "Otomatik optimizasyon durduruldu (Manuel Mod)."
    },
    "toast.index_created_title": {
        "en": "INDEX CREATED",
        "tr": "İNDEKS OLUŞTURULDU"
    },
    "toast.index_created_msg": {
        "en": "[{name}] index successfully created on SQL Server!\nYou can click [Test] to verify performance.",
        "tr": "[{name}] indeksi SQL Server üzerinde başarıyla oluşturuldu!\nPerformansı test etmek için [Test] butonuna basabilirsiniz."
    },
    "toast.index_error_title": {
        "en": "INDEX CREATION ERROR",
        "tr": "İNDEKS OLUŞTURMA HATASI"
    },
    "toast.benchmark_done_title": {
        "en": "BENCHMARK COMPLETED",
        "tr": "BENCHMARK TAMAMLANDI"
    },
    "toast.benchmark_done_msg": {
        "en": "[{title}] live execution time: {ms} ms",
        "tr": "[{title}] canlı yürütme süresi: {ms} ms"
    },
    "toast.benchmark_error_title": {
        "en": "BENCHMARK ERROR",
        "tr": "BENCHMARK HATASI"
    },
    "toast.index_deleted_title": {
        "en": "INDEX REMOVED",
        "tr": "İNDEKS SİLİNDİ"
    },
    "toast.index_deleted_msg": {
        "en": "[{name}] index dropped from SQL Server and RAM cache cleared.",
        "tr": "[{name}] indeksi SQL Server'dan silindi ve RAM önbelleği temizlendi."
    },
    "toast.delete_error_title": {
        "en": "DELETE ERROR",
        "tr": "SİLME HATASI"
    },
    "toast.no_select_title": {
        "en": "NO SELECTION",
        "tr": "SEÇİM YAPILMADI"
    },
    "toast.no_select_msg": {
        "en": "Please select the queries you want to delete using the checkboxes.",
        "tr": "Lütfen silmek istediğiniz sorguları yanlarındaki kutucuklardan seçin."
    },
    "toast.queries_deleted_title": {
        "en": "QUERIES DELETED",
        "tr": "SORGULAR SİLİNDİ"
    },
    "toast.queries_deleted_msg": {
        "en": "{cnt} queries successfully removed from table.",
        "tr": "{cnt} adet sorgu başarıyla tablodan kaldırıldı."
    },
    "toast.all_cleared_title": {
        "en": "ALL CLEARED",
        "tr": "TÜMÜ TEMİZLENDİ"
    },
    "toast.all_cleared_msg": {
        "en": "All query records have been reset.",
        "tr": "Tüm sorgu kayıtları başarıyla sıfırlandı."
    },
    "toast.auto_index_applied_title": {
        "en": "AUTONOMOUS INDEX APPLIED",
        "tr": "OTONOM İNDEKS UYGULANDI"
    },
    "toast.auto_index_applied_msg": {
        "en": "{cnt} optimal indexes automatically applied to SQL Server (Quota: {quota}).",
        "tr": "{cnt} adet optimum indeks otomatik olarak SQL Server'a uygulandı (Kota: {quota})."
    },
    "toast.mode_saved_title": {
        "en": "MODE SAVED",
        "tr": "MOD KAYDEDİLDİ"
    },
    "toast.mode_saved_msg": {
        "en": "Operating mode set to {mode}.",
        "tr": "Çalışma modu {mode} olarak ayarlandı."
    },

}


def init_i18n():
    """Initializes global active language from saved configuration."""
    global _ACTIVE_LANG
    try:
        cfg = get_config()
        lang = getattr(cfg, "language", "en")
        _ACTIVE_LANG = "tr" if str(lang).lower().startswith("tr") else "en"
    except Exception:
        _ACTIVE_LANG = "en"


def get_language() -> str:
    """Returns active language code ('en' or 'tr')."""
    return _ACTIVE_LANG


def set_language(lang: str) -> str:
    """Sets the active language code ('en' or 'tr') and persists to configuration."""
    global _ACTIVE_LANG
    _ACTIVE_LANG = "tr" if str(lang).lower().startswith("tr") else "en"
    try:
        update_language(_ACTIVE_LANG)
    except Exception:
        pass
    return _ACTIVE_LANG


def t(key: str, **kwargs: Any) -> str:
    """Translates a key into current language with optional keyword arguments."""
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key

    raw_text = entry.get(_ACTIVE_LANG) or entry.get("en") or key
    if kwargs:
        try:
            return raw_text.format(**kwargs)
        except Exception:
            return raw_text
    return raw_text


# Initialize active language on module load
init_i18n()
