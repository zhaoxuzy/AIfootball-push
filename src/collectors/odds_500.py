import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright
from src.utils import now_str

async def collect_500_odds(match):
    """
    从500彩票网竞彩赛程页直接抓取赔率数据。
    赛程页结构：每行包含比赛编号、联赛、时间、主队、客队、赔率等。
    本函数定位到目标比赛行，提取该行中的赔率数字。
    """
    data = {
        "胜平负": {
            "初赔": {"主胜": None, "平": None, "客胜": None, "时间": None},
            "即赔": {"主胜": None, "平": None, "客胜": None, "时间": None}
        },
        "让球胜平负": {
            "官方让球数": None,
            "初赔": {"让胜": None, "让平": None, "让负": None, "时间": None},
            "即赔": {"让胜": None, "让平": None, "让负": None, "时间": None}
        },
        "比分赔率": None,
        "总进球赔率": None,
        "半全场赔率": None,
        "返还率": {
            "胜平负返还率": None,
            "让球胜平负返还率": None
        },
        "是否单关": None,
        "查询时间": now_str()
    }

    base_url = "https://trade.500.com/jczq/"
    match_no = match.get("match_no", "")       # 如 "周三003"
    home_team = match.get("home_team", "")     # 如 "水户蜀葵"
    away_team = match.get("away_team", "")     # 如 "鹿岛鹿角"

    debug_dir = Path("output/debug_500")
    debug_dir.mkdir(parents=True, exist_ok=True)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            page.set_default_timeout(20000)

            print(f"[500彩票网] 打开赛程页: {base_url}")
            await page.goto(base_url, wait_until="domcontentloaded")
            # 等待页面加载完成，可能需要更久
            await page.wait_for_timeout(8000)

            # 保存调试文件
            try:
                await page.screenshot(path=str(debug_dir / "500_schedule.png"), full_page=True)
                with open(debug_dir / "500_schedule.html", "w", encoding="utf-8") as f:
                    f.write(await page.content())
                print("[500彩票网] 已保存赛程页调试文件")
            except Exception as e:
                print(f"[500彩票网] 保存调试文件失败: {e}")

            # 定位目标比赛行
            row = None
            # 优先使用比赛编号定位
            try:
                locator = page.locator(f"text={match_no}").first
                if await locator.count() > 0:
                    row = locator.locator("xpath=ancestor::tr[1]")
                    if await row.count() == 0:
                        row = locator.locator("xpath=ancestor::div[contains(@class,'row') or contains(@class,'tr')][1]")
                    print(f"[500彩票网] 通过比赛编号定位到行")
            except Exception as e:
                print(f"[500彩票网] 用比赛编号定位失败: {e}")

            # 如果未找到，尝试用主队名称
            if row is None or await row.count() == 0:
                try:
                    locator = page.locator(f"text={home_team}").first
                    if await locator.count() > 0:
                        row = locator.locator("xpath=ancestor::tr[1]")
                        if await row.count() == 0:
                            row = locator.locator("xpath=ancestor::div[contains(@class,'row') or contains(@class,'tr')][1]")
                        print(f"[500彩票网] 通过主队名称定位到行")
                except Exception as e:
                    print(f"[500彩票网] 用主队名称定位失败: {e}")

            # 如果还未找到，尝试用客队名称
            if row is None or await row.count() == 0:
                try:
                    locator = page.locator(f"text={away_team}").first
                    if await locator.count() > 0:
                        row = locator.locator("xpath=ancestor::tr[1]")
                        if await row.count() == 0:
                            row = locator.locator("xpath=ancestor::div[contains(@class,'row') or contains(@class,'tr')][1]")
                        print(f"[500彩票网] 通过客队名称定位到行")
                except Exception as e:
                    print(f"[500彩票网] 用客队名称定位失败: {e}")

            if row is None or await row.count() == 0:
                print("[500彩票网] 未能定位到比赛行，跳过")
                return data

            # 获取该行的文本，用于调试
            row_text = await row.inner_text()
            print(f"[500彩票网] 目标比赛行文本:\n{row_text}")

            # 提取该行内所有数字（赔率）
            numbers = re.findall(r"\d+\.\d+", row_text)
            print(f"[500彩票网] 提取到的数字: {numbers}")

            # 假设行内数字顺序为：胜平负初赔(3个), 胜平负即赔(3个), 让球初赔(3个), 让球即赔(3个) 等
            # 我们至少提取前6个作为胜平负初赔/即赔
            if len(numbers) >= 6:
                data["胜平负"]["初赔"]["主胜"] = numbers[0]
                data["胜平负"]["初赔"]["平"] = numbers[1]
                data["胜平负"]["初赔"]["客胜"] = numbers[2]
                data["胜平负"]["即赔"]["主胜"] = numbers[3]
                data["胜平负"]["即赔"]["平"] = numbers[4]
                data["胜平负"]["即赔"]["客胜"] = numbers[5]
                print("[500彩票网] 已填充胜平负初赔/即赔")
            else:
                print("[500彩票网] 数字不足6个，无法填充胜平负赔率")

            # 尝试提取让球数（可能为 +1、-1 等格式）
            handicap_match = re.search(r"([+-]\d+)", row_text)
            if handicap_match:
                data["让球胜平负"]["官方让球数"] = handicap_match.group(1)
                print(f"[500彩票网] 让球数: {data['让球胜平负']['官方让球数']}")

            # 如果行内数字较多（可能包含让球赔率），我们可以尝试提取前6个作为胜平负，后6个作为让球胜平负
            if len(numbers) >= 12:
                data["让球胜平负"]["初赔"]["让胜"] = numbers[6]
                data["让球胜平负"]["初赔"]["让平"] = numbers[7]
                data["让球胜平负"]["初赔"]["让负"] = numbers[8]
                data["让球胜平负"]["即赔"]["让胜"] = numbers[9]
                data["让球胜平负"]["即赔"]["让平"] = numbers[10]
                data["让球胜平负"]["即赔"]["让负"] = numbers[11]
                print("[500彩票网] 已填充让球胜平负初赔/即赔")
            else:
                print("[500彩票网] 数字不足12个，未填充让球胜平负赔率（可能页面未显示）")

            await browser.close()
    except Exception as e:
        print(f"[500彩票网] 采集异常: {e}")

    return data
