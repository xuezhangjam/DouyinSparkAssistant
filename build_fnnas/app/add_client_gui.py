import sys
import json
import os
import asyncio
from playwright.async_api import async_playwright

async def main(client_id, alias, friends_str):
    CONFIG_FILE = "clients.json"
    friends = [f.strip() for f in friends_str.split(',')] if friends_str and friends_str.strip() else []
    
    user_data_dir = f"user_data_{client_id}"
    full_user_data_dir = os.path.join(os.getcwd(), user_data_dir)
    
    print(f"即将启动浏览器进行【{alias}】的首次扫码授权...")
    print("==========================================================")
    print("【重要操作提示】：")
    print("1. 浏览器打开后，请立刻扫码登录抖音。")
    print("2. 登录成功且能看到界面后，【请直接点击右上角的 X 关闭浏览器窗口】！")
    print("3. 浏览器关闭后，您的登录状态就会自动保存，录入完成。")
    print("==========================================================")
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=full_user_data_dir,
            headless=False,
            viewport={'width': 1280, 'height': 800},
            args=['--disable-blink-features=AutomationControlled']
        )
        
        page = context.pages[0]
        await page.goto("https://www.douyin.com/")
        
        # 等待页面被用户手动关闭
        try:
            await page.wait_for_event("close", timeout=0)
        except Exception:
            pass
            
        try:
            await context.close()
        except Exception:
            pass
        
    print(f"✅ 浏览器已关闭，状态保存完毕。")
    
    # 更新配置
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            try:
                config = json.load(f)
            except:
                pass
                
    config[client_id] = {
        "alias": alias,
        "status": "active",
        "friends": friends,
        "user_data_dir": user_data_dir,
    }
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
        
    print(f"✅ 客户【{alias}】录入成功并已加入数据库！")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("参数不足")
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3]))
