"""Console worker, also built as SparkWorker.exe for the windowed application."""
import argparse
import asyncio
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

from windows_core import configure_browser_path, contain_worker_processes, data_directory, read_json, validate_clients


async def browser_check():
    from playwright.async_api import async_playwright
    with tempfile.TemporaryDirectory(prefix="spark-check-") as profile:
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(profile, headless=True)
            page = context.pages[0]
            await page.set_content("<title>Spark Windows check</title><h1>火花助手</h1>")
            assert await page.title() == "Spark Windows check"
            await context.close()
    print("浏览器自检通过：独立浏览器可正常启动，中文页面读取成功。", flush=True)


def main():
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["run", "browser", "check"])
    parser.add_argument("client_id", nargs="?")
    args = parser.parse_args()
    job = contain_worker_processes()
    configure_browser_path()
    directory = data_directory()
    os.chdir(directory)
    os.environ["SPARK_PROGRESS_STDOUT"] = "1"
    if args.mode == "check":
        asyncio.run(browser_check())
        return 0
    clients = validate_clients(read_json(directory / "clients.json"), directory)
    if args.client_id not in clients:
        raise ValueError("客户不存在，请先录入客户。")
    if args.mode == "browser":
        from open_browser import main as open_browser
        asyncio.run(open_browser(args.client_id))
        return 0
    if not clients[args.client_id].get("friends"):
        raise ValueError("尚未配置好友名单，请先编辑客户。")
    import runner
    result = asyncio.run(runner.main(args.client_id))
    return result or 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
