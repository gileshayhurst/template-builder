import threading
import webbrowser
from app import app
from config import PORT


def open_browser():
    webbrowser.open(f"http://localhost:{PORT}")


if __name__ == "__main__":
    threading.Timer(1.2, open_browser).start()
    app.run(port=PORT, debug=False)
