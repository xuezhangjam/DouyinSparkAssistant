import sys
import os
import json
import asyncio
from playwright.async_api import async_playwright

async def main(client_id):
    CONFIG_FILE = "clients.json"
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    if client_id not in config:
        print(f"❌ 找不到客户 {client_id}")
        return
        
    client = config[client_id]
    alias = client.get("alias", client_id)
    user_data_dir = client.get("user_data_dir", f"user_data_{client_id}")
    full_user_data_dir = os.path.join(os.getcwd(), user_data_dir)
    
    print(f"=======================================")
    print(f"🌐 正在为客户【{alias}】打开浏览器...")
    print(f"你可以进行任何手动操作（回复消息、检查登录等）")
    print(f"操作完成后，请手动关闭浏览器窗口！")
    print(f"=======================================")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=full_user_data_dir,
            headless=False,
            viewport={'width': 1280, 'height': 800},
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # 拦截所有的非 HTTP(S) 协议（例如 douyin://），防止弹出 "要打开 Dummy Protocol Handler 吗"
        async def intercept_protocol(route):
            if not route.request.url.startswith(('http://', 'https://', 'data:', 'blob:', 'ws://', 'wss://')):
                await route.abort()
            else:
                await route.fallback()
        await context.route("**/*", intercept_protocol)
        
        page = context.pages[0]
        await page.goto("https://www.douyin.com/chat?isPopup=1")
        
        try:
            await page.wait_for_event("close", timeout=0)
        except Exception:
            pass
            
        try:
            await context.close()
        except Exception:
            pass
            
    print(f"✅ 浏览器已关闭。")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("缺少 client_id 参数")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
