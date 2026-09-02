"""VortexDBA - Native Desktop Application Wrapper.

Runs the embedded FastAPI backend and renders the user interface
inside a dedicated, native desktop window using Microsoft Edge WebView2 (pywebview).
Provides a 100% standalone desktop software experience without browser tabs or address bars.
"""

import os
import sys
import time
import socket
import threading
from pathlib import Path

# Add src to sys.path
SRC_DIR = Path(__file__).parent.resolve()
ROOT_DIR = SRC_DIR.parent.resolve()
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import uvicorn
from web_app import app


def find_free_port(start_port: int = 8000) -> int:
    """Find a free local port to bind the embedded server."""
    for port in range(start_port, start_port + 50):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return 8000


def run_backend_server(port: int) -> None:
    """Run FastAPI Uvicorn server in an embedded daemon thread."""
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    server.run()


def wait_for_server(port: int, timeout: float = 5.0) -> bool:
    """Wait until the backend server is ready to accept connections."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    return True
        except Exception:
            pass
        time.sleep(0.1)
    return False


def launch_desktop():
    """Launch the native desktop window."""
    port = find_free_port(8000)

    # Start FastAPI backend in a background thread
    server_thread = threading.Thread(target=run_backend_server, args=(port,), daemon=True)
    server_thread.start()

    # Wait for server readiness
    if not wait_for_server(port, timeout=6.0):
        print(f"[HATA] Arka plan sunucusu 127.0.0.1:{port} adresinde başlatılamadı.")
        sys.exit(1)

    app_url = f"http://127.0.0.1:{port}"
    print(f"[*] VortexDBA Masaüstü Motoru Başlatıldı: {app_url}")

    try:
        import webview

        # Create native desktop window
        window = webview.create_window(
            title="VortexDBA - Autonomous AI Index Advisor",
            url=app_url,
            width=1360,
            height=860,
            min_size=(1024, 700),
            background_color="#08080c",
            text_select=True,
            confirm_close=False,
        )

        # Start native desktop window loop
        webview.start(gui="edgechromium", debug=False)

    except Exception as e:
        print(f"[*] Native WebView penceresi açılamadı ({e}), Native App-Mode başlatılıyor...")
        # Fallback to Windows Edge / Chrome native app-mode
        import subprocess
        edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        
        if os.path.exists(edge_path):
            subprocess.run([edge_path, f"--app={app_url}", "--window-size=1360,860"])
        elif os.path.exists(chrome_path):
            subprocess.run([chrome_path, f"--app={app_url}", "--window-size=1360,860"])
        else:
            import webbrowser
            webbrowser.open(app_url)
            # Keep process alive
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    launch_desktop()
