import os
import time
import psutil
import subprocess
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --------------------------------------------------------------------------------
# opensource_ytmusic_monitor.py
# A generic, open-source version of the YouTube Music playback monitor.
# Usage:
#   python opensource_ytmusic_monitor.py \
#       --chrome-binary /path/to/chrome \
#       --chromedriver /path/to/chromedriver \
#       --user-data-dir /path/to/chrome/user/data \
#       [--debug-port PORT]
# --------------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Monitor YouTube Music playback and log tracks to a file."
    )
    parser.add_argument(
        "--chrome-binary", required=True,
        help="Path to the Chrome executable"
    )
    parser.add_argument(
        "--chromedriver", required=True,
        help="Path to chromedriver executable"
    )
    parser.add_argument(
        "--user-data-dir", required=True,
        help="Chrome user data directory"
    )
    parser.add_argument(
        "--debug-port", type=int, default=9222,
        help="Remote debugging port (default: 9222)"
    )
    parser.add_argument(
        "--log-file", default="playlist_log.txt",
        help="File to append track logs (default: playlist_log.txt)"
    )
    parser.add_argument(
        "--wait-time", type=int, default=15,
        help="Seconds to wait for Chrome to launch (default: 15)"
    )
    return parser.parse_args()


def kill_existing_chrome():
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] in ('chrome.exe', 'chromedriver.exe'):
            try:
                proc.kill()
            except psutil.NoSuchProcess:
                pass


def verify_paths(chrome_binary, chromedriver_path, user_data_dir):
    errors = []
    if not os.path.isfile(chrome_binary):
        errors.append(f"Chrome not found at {chrome_binary}")
    if not os.path.isfile(chromedriver_path):
        errors.append(f"ChromeDriver not found at {chromedriver_path}")
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        exit(1)


def launch_chrome(chrome_binary, user_data_dir, debug_port):
    os.makedirs(user_data_dir, exist_ok=True)
    cmd = [
        chrome_binary,
        f"--remote-debugging-port={debug_port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--new-window",
        "https://music.youtube.com"
    ]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def connect_driver(chromedriver_path, debug_port):
    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
    service = Service(executable_path=chromedriver_path)
    return webdriver.Chrome(service=service, options=options)


def main():
    args = parse_args()
    print("[1/5] Cleaning up existing Chrome instances...")
    kill_existing_chrome()
    print("[2/5] Verifying provided paths...")
    verify_paths(args.chrome_binary, args.chromedriver, args.user_data_dir)
    print("[3/5] Launching Chrome...")
    launch_chrome(args.chrome_binary, args.user_data_dir, args.debug_port)

    print(f"[4/5] Waiting {args.wait_time} seconds for Chrome to initialize...")
    time.sleep(args.wait_time)

    print("[5/5] Connecting to Chrome via WebDriver...")
    driver = connect_driver(args.chromedriver, args.debug_port)

    try:
        print("Waiting for YouTube Music page to load...")
        WebDriverWait(driver, 30).until(
            EC.url_contains("music.youtube.com")
        )
        print("✔ YouTube Music loaded. Complete login manually and start playback.")
        input("Press ENTER to start monitoring...")

        prev_title = None
        print("Monitoring playback (Ctrl+C to exit)...")
        while True:
            try:
                title_el = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "ytmusic-player-bar .title"))
                )
                artist_el = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "ytmusic-player-bar .byline a"))
                )
                title = title_el.text
                artist = artist_el.text
                if title != prev_title:
                    print(f"Now Playing: {artist} - {title}")
                    with open(args.log_file, "a", encoding="utf-8") as f:
                        f.write(f"{title}|{artist}\n")
                    prev_title = title
                time.sleep(3)
            except Exception as e:
                print(f"Warning: {e}")
                time.sleep(5)
    except KeyboardInterrupt:
        print("Monitoring stopped by user.")
    finally:
        driver.quit()
        print("Chrome connection closed.")

if __name__ == "__main__":
    main()
