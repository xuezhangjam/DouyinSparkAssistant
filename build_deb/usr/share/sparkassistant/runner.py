import asyncio
from playwright.async_api import async_playwright, Error as PlaywrightError

import sys
import json
import os
import random

CONFIG_FILE = "clients.json"

async def main(client_id):
    # 读取配置
    if not os.path.exists(CONFIG_FILE):
        print(f"配置文件 {CONFIG_FILE} 不存在，请先录入客户！")
        return
    
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    if client_id not in config:
        print(f"客户 {client_id} 不存在！")
        return
        
    client_config = config[client_id]
    user_data_dir = os.path.join(os.getcwd(), client_config.get("user_data_dir", f"user_data_{client_id}"))
    friends = client_config.get("friends", [])
    
    if not friends:
        print(f"客户 {client_id} 没有配置任何需要续火花的好友，退出。")
        return

    async with async_playwright() as p:
        # 根据环境变量决定是否使用无头模式
        is_headless = os.environ.get("DOUYIN_HEADLESS", "true").lower() == "true"
        is_test_mode = os.environ.get("DOUYIN_TEST_MODE", "false").lower() == "true"
        
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=is_headless,
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
        
        async def safe_click(x, y):
            # 增加随机偏移量（-3到3像素），模拟真实人类手抖，降低风控概率
            x = x + random.uniform(-3.0, 3.0)
            y = y + random.uniform(-3.0, 3.0)
            
            if is_test_mode:
                print(f"🖱️ 【测试模式】模拟点击坐标: (X: {x:.1f}, Y: {y:.1f})")
                await page.evaluate(f'''() => {{
                    const dot = document.createElement('div');
                    dot.style.position = 'fixed';
                    dot.style.left = '{x - 10}px';
                    dot.style.top = '{y - 10}px';
                    dot.style.width = '20px';
                    dot.style.height = '20px';
                    dot.style.backgroundColor = 'rgba(255, 0, 0, 0.6)';
                    dot.style.border = '2px solid white';
                    dot.style.borderRadius = '50%';
                    dot.style.zIndex = '2147483647';
                    dot.style.pointerEvents = 'none';
                    dot.style.transition = 'all 0.8s ease-out';
                    dot.style.boxShadow = '0 0 10px red';
                    document.body.appendChild(dot);
                    setTimeout(() => {{ dot.style.transform = 'scale(2.5)'; dot.style.opacity = '0'; }}, 50);
                    setTimeout(() => dot.remove(), 900);
                }}''')
            await page.mouse.click(x, y)

        async def safe_press(key):
            if is_test_mode:
                print(f"⌨️ 【测试模式】模拟按键: {key}")
                await page.evaluate(f'''() => {{
                    const toast = document.createElement('div');
                    toast.textContent = '⌨️ 模拟按键: {key}';
                    toast.style.position = 'fixed';
                    toast.style.bottom = '20px';
                    toast.style.right = '20px';
                    toast.style.padding = '10px 20px';
                    toast.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
                    toast.style.color = 'white';
                    toast.style.borderRadius = '8px';
                    toast.style.zIndex = '2147483647';
                    toast.style.fontFamily = 'monospace';
                    toast.style.fontSize = '16px';
                    toast.style.transition = 'opacity 1s';
                    toast.style.pointerEvents = 'none';
                    document.body.appendChild(toast);
                    setTimeout(() => {{ toast.style.opacity = '0'; }}, 1500);
                    setTimeout(() => toast.remove(), 2500);
                }}''')
            await page.keyboard.press(key)
        
        # 拦截所有打开新标签页的请求
        await page.route("**/*", lambda route: route.continue_())

        print("正在打开 https://www.douyin.com/chat?isPopup=1 ...")
        await page.goto("https://www.douyin.com/chat?isPopup=1")
        
        print("等待页面加载（前 5 秒）...")
        await asyncio.sleep(5)
        
        # 安全风控检测：检查是否出现了登录/验证码弹窗
        is_login_modal = await page.evaluate('''() => {
            const text = document.body.innerText;
            return text.includes('登录后免费畅享高清视频') || text.includes('一键登录') || text.includes('验证码发送太频繁');
        }''')
        
        if is_login_modal:
            print("\\n❌❌❌ 遭遇安全风控拦截 ❌❌❌")
            print(f"客户 {client_id} 的登录状态已失效，或触发了抖音的安全验证弹窗！")
            print("💡 【解决办法】：")
            print("1. 在左侧客户列表中选中该客户")
            print("2. 点击操作栏的【🌐 调试浏览器】")
            print("3. 在弹出的浏览器中手动完成登录或短信验证")
            print("4. 登录成功后直接关闭浏览器即可恢复！")
            print("======================================")
            await asyncio.sleep(2)
            return 2

        print(f"✅ 成功锁定这 {len(friends)} 位好友，准备按名字逐一追踪并续火花：")
        print(" | ".join(friends))

        # ---------------------------------------------------------
        # 2. 依次按名字定位并续火花
        # ---------------------------------------------------------
        for friend_name in friends:
            print(f"\\n======================================")
            print(f"▶️ 正在追踪好友: {friend_name}")
            
            # 每次寻找新朋友前，先把左侧列表滚回到最顶部，防止漏掉上面的人
            await page.mouse.move(150, 400)
            await page.mouse.wheel(0, -10000)
            await asyncio.sleep(1)
            
            # 定位并点击该好友 (带滚动重试)
            found_box = None
            for attempt in range(8):
                found_box = await page.evaluate(f'''() => {{
                    const els = Array.from(document.querySelectorAll('*'))
                        .filter(el => el.textContent && el.textContent.includes('{friend_name}') && el.childElementCount === 0);
                    if (els.length > 0) {{
                        const el = els[els.length-1];
                        const rect = el.getBoundingClientRect();
                        if (rect.height > 0) {{
                            el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            return {{x: rect.x, y: rect.y, w: rect.width, h: rect.height}};
                        }}
                    }}
                    return null;
                }}''')
                
                if found_box:
                    break
                    
                print(f"🔄 当前可视区未发现【{friend_name}】，尝试向下滚动聊天列表...")
                # 将鼠标移动到左侧聊天列表区域并滚动
                await page.mouse.move(150, 400)
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(2)
                
            if found_box:
                # 重新获取滚动后的绝对坐标
                final_box = await page.evaluate(f'''() => {{
                    const els = Array.from(document.querySelectorAll('*'))
                        .filter(el => el.textContent && el.textContent.includes('{friend_name}') && el.childElementCount === 0);
                    const rect = els[els.length-1].getBoundingClientRect();
                    return {{x: rect.x, y: rect.y, w: rect.width, h: rect.height}};
                }}''')
                
                if not final_box:
                    continue
                    
                # 在 x 轴增加较大随机偏移 (5~40像素)，模拟点在空白区域的随机位置
                click_x = final_box['x'] + random.uniform(5, 40)
                click_y = final_box['y'] + final_box['h'] + 12
                
                # 在移动鼠标时，分段模拟人类轨迹
                await page.mouse.move(click_x + random.uniform(-10, 10), click_y + random.uniform(-5, 5))
                await asyncio.sleep(0.1)
                await page.mouse.move(click_x, click_y)
                await asyncio.sleep(0.5)
                await safe_click(click_x, click_y)
                print(f"✅ 已成功通过检测名字锁定【{friend_name}】，并安全点击了其正下方的【聊天预览空白区】")
            else:
                print(f"⚠️ 翻遍了列表也未能找到名字包含【{friend_name}】的元素，自动回到列表顶部...")
                # 找不到人的时候，把鼠标移回左侧列表并往上狂滚，回到顶部，防止影响下一个人的寻找
                await page.mouse.move(150, 400)
                await page.mouse.wheel(0, -10000)
                await asyncio.sleep(1)
                continue
            
            # 等待聊天框加载完成
            await asyncio.sleep(3)
            
            # 点击笑脸菜单
            print("实时定位表情菜单按钮...")
            smile_box = await page.evaluate('''() => {
                const btn = document.querySelector('svg.messageMsgInputiconAction');
                if (btn) {
                    const rect = btn.getBoundingClientRect();
                    return {x: rect.x, y: rect.y, w: rect.width, h: rect.height};
                }
                return null;
            }''')
            
            if smile_box:
                # 使用鼠标真实的绝对坐标点击，100% 触发前端 React 监听器
                await safe_click(smile_box['x'] + smile_box['w']/2, smile_box['y'] + smile_box['h']/2)
                print("✅ 已成功点击笑脸菜单")
                await asyncio.sleep(2)
                
                # 寻找并点击续火花表情
                print("实时识别菜单中的【续火花】表情...")
                huohua_clicked = await page.evaluate('''() => {
                    // 找文字包含"续火花"的元素
                    const els = Array.from(document.querySelectorAll('*')).filter(el => el.textContent === '续火花');
                    if (els.length > 0) {
                        const textEl = els[els.length-1];
                        const parent = textEl.parentElement;
                        if(parent) {
                            const imgBox = parent.querySelector('[data-apm-action=\"EmojiItem\"]') || parent;
                            if ("''' + str(is_test_mode).lower() + '''" === "true") {
                                imgBox.style.border = "3px solid red";
                                imgBox.scrollIntoView({behavior: "smooth", block: "center"});
                            } else {
                                imgBox.click();
                            }
                            return true;
                        }
                    }
                    return false;
                }''')
                
                if huohua_clicked:
                    if is_test_mode:
                        print("🧪 【测试模式】已定位到“续火花”表情并高亮，跳过发送操作。")
                        await asyncio.sleep(3)
                        # 关闭表情面板，防止它的透明遮罩拦截下一个人的点击
                        await safe_press("Escape")
                        await safe_click(10, 10)
                    else:
                        print("✅ 已成功点击“续火花”表情！")
                        await asyncio.sleep(1)
                        
                        # 抖音网页版的表情可能只是填入了输入框，或者已经直接发出(贴纸)。
                        # 为了保险，尝试点击发送按钮或回车。
                        await page.evaluate('''() => {
                            const btn = document.querySelector('.e2e-send-msg-btn, .messageMsgInputpublishBtn');
                            if (btn) {
                                const clickTarget = btn.closest('div') || btn;
                                clickTarget.click();
                            }
                        }''')
                        print("✅ 火花已成功发送！")
                        
                        await asyncio.sleep(2)
                else:
                    print("⚠️ 未找到续火花表情。尝试发送第一个推荐表情...")
                    fallback_clicked = await page.evaluate('''() => {
                        const firstItem = document.querySelector('.emoji-panel [data-apm-action=\"EmojiItem\"], .emojiEmojiItemimgBox');
                        if (firstItem) {
                            if ("''' + str(is_test_mode).lower() + '''" === "true") {
                                firstItem.style.border = "3px solid red";
                                firstItem.scrollIntoView({behavior: "smooth", block: "center"});
                            } else {
                                firstItem.click();
                            }
                            return true;
                        }
                        return false;
                    }''')
                    if fallback_clicked:
                        if is_test_mode:
                            print("🧪 【测试模式】已定位到备用表情并高亮，跳过发送操作。")
                            await asyncio.sleep(3)
                            # 关闭表情面板
                            await safe_press("Escape")
                            await safe_click(10, 10)
                        else:
                            print("✅ 已点击第一个备用表情")
                            await asyncio.sleep(1)
                            
                            await page.evaluate('''() => {
                                const btn = document.querySelector('.e2e-send-msg-btn, .messageMsgInputpublishBtn');
                                if (btn) {
                                    const clickTarget = btn.closest('div') || btn;
                                    clickTarget.click();
                                }
                            }''')
                            print("✅ 备用表情已成功发送！")
                                
                            await asyncio.sleep(2)
                    else:
                        print("❌ 表情面板中没有找到任何可点击的表情")
            else:
                print("❌ 未能在右侧聊天框底部找到表情(笑脸)图标")
                
            await asyncio.sleep(2)
        
        print("\\n🎉 自动化流程结束。浏览器将在 5 秒后自动关闭...")
        await asyncio.sleep(5)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python runner.py <client_id>")
        sys.exit(1)
    try:
        ret = asyncio.run(main(sys.argv[1]))
        if ret is not None:
            sys.exit(ret)
    except PlaywrightError as e:
        if "has been closed" in str(e) or "TargetClosedError" in str(type(e)):
            print("\n==================================================")
            print("🛑 任务中止：检测到您已手动关闭浏览器，运行自动终止。")
            sys.exit(1)
        else:
            raise
    except KeyboardInterrupt:
        print("\n==================================================")
        print("🛑 任务中止：用户手动停止运行。")
        sys.exit(1)
