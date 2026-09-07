import uvicorn
import webbrowser
import os
import sys

def main():
    port = 8000
    host = "127.0.0.1"
    url = f"http://{host}:{port}"
    
    print("=" * 60)
    print(f"🚀 PixelBoost PropLeadAi — Real Estate Lead Scraper & CRM")
    print(f"Made with ❤️ By CK")
    print(f"Dashboard URL: http://{host}:{port}")
    print("=" * 60)
    print(f"💡 Press Ctrl+C to stop the server\n")
    
    # Try opening the browser automatically
    try:
        webbrowser.open(url)
    except Exception:
        pass

    uvicorn.run("app:app", host=host, port=port, reload=False, log_level="info")

if __name__ == "__main__":
    main()
