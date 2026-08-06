import os

with open("/tmp/original_runner.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_code = """        # ---------------------------------------------------------
        # 2. 依次按名字定位并续火花 (优化：就近原则扫描)
        # ---------------------------------------------------------
        pending_friends = set(friends)
        
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
                print(f"\\n======================================")
                print(f"📍 就近发现未处理好友: {friend_name}")
                
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
                
                await asyncio.sleep(3)
                
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
                    await safe_click(smile_box['x'] + smile_box['w']/2, smile_box['y'] + smile_box['h']/2)
                    print("✅ 已成功点击笑脸菜单")
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
"""

new_lines = lines[:134] + [new_code + "\n"] + lines[310:]
with open("/usr/share/sparkassistant/runner.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
