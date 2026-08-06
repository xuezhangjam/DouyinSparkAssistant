import asyncio
from playwright.async_api import async_playwright, Error as PlaywrightError

import sys
import json
import os
import random
import subprocess

zenity_process = None

def init_progress():
    global zenity_process
    
    # 在 Cron 定时任务等无头环境下，自动探测当前用户的活跃桌面显示器并注入环境变量
    if "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ:
        try:
            output = subprocess.check_output(["w", "-h"], text=True)
            for line in output.split('\n'):
                parts = line.split()
                if len(parts) > 2 and parts[1].startswith(':'):
                    os.environ["DISPLAY"] = parts[1]
                    break
        except Exception:
            pass
        if "DISPLAY" not in os.environ:
            os.environ["DISPLAY"] = ":0"
            
    if "XAUTHORITY" not in os.environ:
        os.environ["XAUTHORITY"] = os.path.expanduser("~/.Xauthority")
        
    try:
        zenity_process = subprocess.Popen(
            ["zenity", "--progress", "--title=火花助手运行中", "--text=正在初始化...", "--percentage=0", "--auto-close", "--width=350", "--no-cancel"],
            stdin=subprocess.PIPE, text=True, stderr=subprocess.DEVNULL
        )
    except Exception:
        zenity_process = None

def update_progress(percent, text):
    global zenity_process
    if zenity_process and zenity_process.poll() is None:
        try:
            zenity_process.stdin.write(f"{percent}\n")
            zenity_process.stdin.write(f"# {text}\n")
            zenity_process.stdin.flush()
        except:
            pass

def close_progress():
    global zenity_process
    if zenity_process and zenity_process.poll() is None:
        try:
            zenity_process.stdin.write("100\n")
            zenity_process.stdin.write("# 任务完成\n")
            zenity_process.stdin.flush()
        except:
            pass

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
        
    init_progress()
    update_progress(5, "启动浏览器环境...")

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
        update_progress(10, "正在打开网页版聊天...")
        await page.goto("https://www.douyin.com/chat?isPopup=1")
        
        print("等待页面加载（前 5 秒）...")
        update_progress(15, "等待页面加载...")
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
            update_progress(100, "遭遇安全风控拦截，请手动处理！")
            await asyncio.sleep(2)
            close_progress()
            return 2

        print(f"✅ 成功锁定这 {len(friends)} 位好友，准备按名字逐一追踪并续火花：")
        print(" | ".join(friends))
        update_progress(20, f"锁定 {len(friends)} 位好友，开始扫描...")

        # ---------------------------------------------------------
        # 2. 依次按名字定位并续火花 (优化：就近原则扫描)
        # ---------------------------------------------------------
        pending_friends = set(friends)
        total_friends = len(friends)
        
        # 先把左侧列表滚回到最顶部
        await page.mouse.move(150, 400)
        await page.mouse.wheel(0, -10000)
        await asyncio.sleep(1)
        
        print(f"▶️ 开始按列表就近原则（从上到下）扫描好友...")
        
        for attempt in range(40):
            if not pending_friends:
                print("✅ 所有目标好友均已处理完毕！")
                break
                
            found_friend = await page.evaluate(f'''(pending) => {{
                const els = Array.from(document.querySelectorAll('*'))
                    .filter(el => {{
                        if (el.childElementCount !== 0 || !el.textContent) return false;
                        const text = el.textContent.trim();
                        // 必须在左侧列表区域 (x < 400, 防止点到右侧聊天框的标题导致进主页)
                        const rect = el.getBoundingClientRect();
                        if (rect.x > 400 || rect.y < 50 || rect.width === 0) return false;
                        // 优先严格全等匹配，防止“学长2”错误匹配“学长”
                        if (pending.includes(text)) return true;
                        return false;
                    }});
                    
                if (els.length > 0) {{
                    const el = els[0];
                    const rect = el.getBoundingClientRect();
                    const text = el.textContent.trim();
                    const name = pending.find(f => text === f);
                    el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                    return {{name: name, x: rect.x, y: rect.y, w: rect.width, h: rect.height}};
                }}
                
                // 如果严格全等没找到，再尝试前缀匹配（应对极少数带有不可见字符的情况）
                const fallbackEls = Array.from(document.querySelectorAll('*'))
                    .filter(el => {{
                        if (el.childElementCount !== 0 || !el.textContent) return false;
                        const text = el.textContent.trim();
                        const rect = el.getBoundingClientRect();
                        if (rect.x > 400 || rect.y < 50 || rect.width === 0) return false;
                        // 按长度排序，优先匹配长的
                        const sorted = [...pending].sort((a,b) => b.length - a.length);
                        return sorted.some(f => text.startsWith(f));
                    }});
                    
                if (fallbackEls.length > 0) {{
                    const el = fallbackEls[0];
                    const text = el.textContent.trim();
                    const sorted = [...pending].sort((a,b) => b.length - a.length);
                    const name = sorted.find(f => text.startsWith(f));
                    el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                    return {{name: name, x: el.getBoundingClientRect().x, y: el.getBoundingClientRect().y}};
                }}
                
                return null;
            }}''', list(pending_friends))
            
            if found_friend:
                friend_name = found_friend['name']
                processed_count = total_friends - len(pending_friends) + 1
                base_pct = 20 + int(70 * processed_count / total_friends)
                
                print(f"\\n======================================")
                print(f"📍 就近发现未处理好友: {friend_name}")
                update_progress(base_pct, f"定位到好友: {friend_name}")
                
                # 等待平滑滚动（smooth scroll）完成！非常重要，否则鼠标会点到滚动前的位置导致乱序点击！
                await asyncio.sleep(1.0)
                
                final_box = await page.evaluate(f'''(name) => {{
                    const els = Array.from(document.querySelectorAll('*'))
                        .filter(el => {{
                            if (el.childElementCount !== 0 || !el.textContent) return false;
                            const rect = el.getBoundingClientRect();
                            if (rect.x > 400 || rect.y < 50 || rect.width === 0) return false;
                            const text = el.textContent.trim();
                            return text === name || text.startsWith(name);
                        }});
                    if (els.length > 0) {{
                        const rect = els[els.length-1].getBoundingClientRect();
                        return {{x: rect.x, y: rect.y, w: rect.width, h: rect.height}};
                    }}
                    return null;
                }}''', friend_name)
                
                if not final_box:
                    print("⚠️ 滚动后未能重新定位到该好友元素，跳过。")
                    continue
                    
                click_x = final_box['x'] + random.uniform(5, 40)
                # 正下方白底区域
                click_y = final_box['y'] + final_box['h'] + 12
                
                await page.mouse.move(click_x + random.uniform(-10, 10), click_y + random.uniform(-5, 5))
                await asyncio.sleep(0.1)
                await page.mouse.move(click_x, click_y)
                await asyncio.sleep(0.5)
                await safe_click(click_x, click_y)
                print(f"✅ 已成功进入【{friend_name}】的聊天框")
                update_progress(base_pct + 1, f"进入【{friend_name}】聊天框...")
                
                await asyncio.sleep(3)
                
                print("实时定位表情菜单按钮...")
                update_progress(base_pct + 2, "查找表情面板...")
                smile_box = await page.evaluate('''() => {
                    const btn = document.querySelector('svg.messageMsgInputiconAction');
                    if (btn) {
                        const rect = btn.getBoundingClientRect();
                        return {x: rect.x, y: rect.y, w: rect.width, h: rect.height};
                    }
                    return null;
                }''')
                
                if smile_box:
                    await safe_click(smile_box['x'] + smile_box['w']/2, smile_box['y'] + smile_box['h']/2)
                    print("✅ 已成功点击笑脸菜单")
                    update_progress(base_pct + 3, "识别续火花表情...")
                    await asyncio.sleep(2)
                    
                    print("实时识别菜单中的【续火花】表情...")
                    huohua_clicked = await page.evaluate('''() => {
                        const els = Array.from(document.querySelectorAll('*')).filter(el => el.textContent === '续火花');
                        if (els.length > 0) {
                            const parent = els[els.length-1].parentElement;
                            if(parent) {
                                const imgBox = parent.querySelector('[data-apm-action="EmojiItem"]') || parent;
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
                            print("🧪 【测试模式】跳过发送操作。")
                            await asyncio.sleep(3)
                            await safe_press("Escape")
                            await safe_click(10, 10)
                        else:
                            print("✅ 已成功点击“续火花”表情！")
                            await asyncio.sleep(1)
                            await page.evaluate('''() => {
                                const btn = document.querySelector('.e2e-send-msg-btn, .messageMsgInputpublishBtn');
                                if (btn) { (btn.closest('div') || btn).click(); }
                            }''')
                            print("✅ 火花已成功发送！")
                            update_progress(base_pct + 4, f"【{friend_name}】火花发送完毕！")
                            await asyncio.sleep(2)
                    else:
                        print("⚠️ 未找到续火花表情。尝试发送第一个推荐表情...")
                        fallback_clicked = await page.evaluate('''() => {
                            const firstItem = document.querySelector('.emoji-panel [data-apm-action="EmojiItem"], .emojiEmojiItemimgBox');
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
                                print("🧪 【测试模式】跳过发送操作。")
                                await asyncio.sleep(3)
                                await safe_press("Escape")
                                await safe_click(10, 10)
                            else:
                                print("✅ 已点击备用表情并发送！")
                                await asyncio.sleep(1)
                                await page.evaluate('''() => {
                                    const btn = document.querySelector('.e2e-send-msg-btn, .messageMsgInputpublishBtn');
                                    if (btn) { (btn.closest('div') || btn).click(); }
                                }''')
                                update_progress(base_pct + 4, f"【{friend_name}】备用表情发送完毕！")
                                await asyncio.sleep(2)
                        else:
                            print("❌ 表情面板中没有可点击的表情")
                else:
                    print("❌ 未能找到笑脸图标")
                    
                pending_friends.remove(friend_name)
                await asyncio.sleep(2)
                continue
                
            print(f"🔄 当前可视区未发现剩余的待处理好友，向下滚动列表...")
            await page.mouse.move(150, 400)
            await page.mouse.wheel(0, 800)
            await asyncio.sleep(1.5)

        
        print("\\n🎉 自动化流程结束。浏览器将在 5 秒后自动关闭...")
        update_progress(95, "自动化流程结束，准备关闭浏览器...")
        await asyncio.sleep(5)
        close_progress()

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
            close_progress()
            sys.exit(1)
        else:
            close_progress()
            raise
    except KeyboardInterrupt:
        print("\n==================================================")
        print("🛑 任务中止：用户手动停止运行。")
        close_progress()
        sys.exit(1)
