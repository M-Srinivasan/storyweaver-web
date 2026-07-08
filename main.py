from app import start_server

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  ✦  STORY WEAVER")
    print("="*60)
    print("  Starting web server at http://127.0.0.1:5000")
    print("  Your browser will open automatically.")
    print("  Press  Ctrl+C  to stop the server.")
    print("="*60 + "\n")
    start_server(host="127.0.0.1", port=5000, open_browser=True)
