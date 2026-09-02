import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright
from src.utils import now_str

async def collect_500_odds(match):
    """
    从500彩票网竞彩页面直接抓取各玩法赔率。
    URL模板：https://trade.500.com/jczq/?playid={playid}&g=2&date={date}
    playid: 269(胜平负/让球), 271(比分), 270(总进球), 272(半全场)
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

    match_no = match.get("match_no", "")        # 如 "周三003"
    match_date = match.get("match_date", "")    # 如 "2026-09-02"
    home_team = match.get("home_team", "")
    away_team = match.get("away_team", "")

    debug_dir = Path("output/debug_500")
    debug_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_page(page, url, wait_time=3000):
        """访问页面并返回 page 对象，自动等待"""
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(wait_time)
        return page

    async def find_match_row(page, match_no, home_team, away_team):
        """在当前页面中定位目标比赛行，返回 row locator 或 None"""
        # 尝试通过比赛编号定位
        locator = page.locator(f"text={match_no}").first
        if await locator.count() > 0:
            row = locator.locator("xpath=ancestor::tr[1]")
            if await row.count() == 0:
                row = locator.locator("xpath=ancestor::div[contains(@class,'row') or contains(@class,'tr')][1]")
            if await row.count() > 0:
                return row

        # 尝试主队名称
        locator = page.locator(f"text={home_team}").first
        if await locator.count() > 0:
            row = locator.locator("xpath=ancestor::tr[1]")
            if await row.count() == 0:
                row = locator.locator("xpath=ancestor::div[contains(@class,'row') or contains(@class,'tr')][1]")
            if await row.count() > 0:
                return row

        # 尝试客队名称
        locator = page.locator(f"text={away_team}").first
        if await locator.count() > 0:
            row = locator.locator("xpath=ancestor::tr[1]")
            if await row.count() == 0:
                row = locator.locator("xpath=ancestor::div[contains(@class,'row') or contains(@class,'tr')][1]")
            if await row.count() > 0:
                return row

        return None

    async def parse_spf_and_rqspf(page, match_no, home_team, away_team):
        """解析胜平负和让球胜平负（playid=269页面）"""
        row = await find_match_row(page, match_no, home_team, away_team)
        if row is None:
            print("[500彩票网] 胜平负/让球页面未找到比赛行")
            return

        row_text = await row.inner_text()
        print(f"[500彩票网] 胜平负/让球行文本:\n{row_text}")

        # 提取所有数字
        numbers = re.findall(r"\d+\.\d+", row_text)
        print(f"[500彩票网] 数字列表: {numbers}")

        # 假设数字顺序：初赔3个，即赔3个，让球初赔3个，让球即赔3个（可能更多）
        if len(numbers) >= 6:
            data["胜平负"]["初赔"]["主胜"] = numbers[0]
            data["胜平负"]["初赔"]["平"] = numbers[1]
            data["胜平负"]["初赔"]["客胜"] = numbers[2]
            data["胜平负"]["即赔"]["主胜"] = numbers[3]
            data["胜平负"]["即赔"]["平"] = numbers[4]
            data["胜平负"]["即赔"]["客胜"] = numbers[5]

        # 让球数：查找 +1、-1 等
        handicap_match = re.search(r"([+-])(\d+)", row_text)
        if handicap_match:
            sign = handicap_match.group(1)
            num = int(handicap_match.group(2))
            data["让球胜平负"]["官方让球数"] = f"{sign}{num}"

        # 如果数字足够多，继续填充让球赔率
        if len(numbers) >= 12:
            data["让球胜平负"]["初赔"]["让胜"] = numbers[6]
            data["让球胜平负"]["初赔"]["让平"] = numbers[7]
            data["让球胜平负"]["初赔"]["让负"] = numbers[8]
            data["让球胜平负"]["即赔"]["让胜"] = numbers[9]
            data["让球胜平负"]["即赔"]["让平"] = numbers[10]
            data["让球胜平负"]["即赔"]["让负"] = numbers[11]
            print("[500彩票网] 已填充让球胜平负赔率")
        else:
            print("[500彩票网] 数字不足12个，让球赔率未填充")

    async def parse_score(page, match_no, home_team, away_team):
        """解析比分赔率（playid=271页面）"""
        # 比分页面默认可能只显示部分场次，需要点击“展开投注”或类似按钮
        try:
            # 尝试点击展开按钮（可能文本为“展开投注”、“显示全部”等）
            expand_btn = page.locator("button:has-text('展开'), a:has-text('展开'), span:has-text('展开')").first
            if await expand_btn.count() > 0:
                await expand_btn.click()
                await page.wait_for_timeout(2000)
                print("[500彩票网] 已点击展开投注按钮")
        except Exception as e:
            print(f"[500彩票网] 点击展开按钮失败: {e}")

        row = await find_match_row(page, match_no, home_team, away_team)
        if row is None:
            print("[500彩票网] 比分页面未找到比赛行")
            return

        row_text = await row.inner_text()
        print(f"[500彩票网] 比分行文本:\n{row_text}")

        # 解析比分赔率：格式可能为 "1:0 6.50 2:0 8.00 ..."
        # 使用正则匹配比分和赔率
        score_pattern = re.findall(r"(\d+[:：-]\d+)\s+(\d+\.\d+)", row_text)
        if score_pattern:
            score_dict = {}
            for score, odds in score_pattern:
                # 统一格式为 "1-0"
                score_clean = score.replace(":", "-").replace("：", "-")
                score_dict[score_clean] = odds
            data["比分赔率"] = score_dict
            print(f"[500彩票网] 已解析比分赔率 {len(score_dict)} 项")
        else:
            print("[500彩票网] 未匹配到比分赔率格式")

    async def parse_total_goals(page, match_no, home_team, away_team):
        """解析总进球赔率（playid=270页面）"""
        row = await find_match_row(page, match_no, home_team, away_team)
        if row is None:
            print("[500彩票网] 总进球页面未找到比赛行")
            return

        row_text = await row.inner_text()
        print(f"[500彩票网] 总进球行文本:\n{row_text}")

        # 总进球赔率格式可能为 "0 6.50 1 4.20 2 3.10 ... 7+ 12.00"
        # 提取所有数字对（进球数, 赔率）
        # 注意7+可能写作"7+"或"7+"
        total_pattern = re.findall(r"(\d\+?)\s+(\d+\.\d+)", row_text)
        if total_pattern:
            total_dict = {}
            for goals, odds in total_pattern:
                total_dict[goals] = odds
            data["总进球赔率"] = total_dict
            print(f"[500彩票网] 已解析总进球赔率 {len(total_dict)} 项")
        else:
            print("[500彩票网] 未匹配到总进球赔率格式")

    async def parse_half_full(page, match_no, home_team, away_team):
        """解析半全场赔率（playid=272页面）"""
        row = await find_match_row(page, match_no, home_team, away_team)
        if row is None:
            print("[500彩票网] 半全场页面未找到比赛行")
            return

        row_text = await row.inner_text()
        print(f"[500彩票网] 半全场行文本:\n{row_text}")

        # 半全场9项：胜胜、胜平、胜负、平胜、平平、平负、负胜、负平、负负
        options = ["胜胜", "胜平", "胜负", "平胜", "平平", "平负", "负胜", "负平", "负负"]
        hf_dict = {}
        for opt in options:
            match = re.search(rf"{opt}\s+(\d+\.\d+)", row_text)
            if match:
                hf_dict[opt] = match.group(1)
        if hf_dict:
            data["半全场赔率"] = hf_dict
            print(f"[500彩票网] 已解析半全场赔率 {len(hf_dict)} 项")
        else:
            print("[500彩票网] 未匹配到半全场赔率格式")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            page.set_default_timeout(30000)

            # 1. 胜平负/让球胜平负 (playid=269)
            url_269 = f"https://trade.500.com/jczq/?playid=269&g=2&date={match_date}"
            print(f"[500彩票网] 访问胜平负页面: {url_269}")
            await fetch_page(page, url_269, wait_time=5000)
            await page.screenshot(path=str(debug_dir / "500_spf.png"), full_page=True)
            with open(debug_dir / "500_spf.html", "w", encoding="utf-8") as f:
                f.write(await page.content())
            await parse_spf_and_rqspf(page, match_no, home_team, away_team)

            # 2. 比分 (playid=271)
            url_271 = f"https://trade.500.com/jczq/?playid=271&g=2&date={match_date}"
            print(f"[500彩票网] 访问比分页面: {url_271}")
            await fetch_page(page, url_271, wait_time=5000)
            await page.screenshot(path=str(debug_dir / "500_score.png"), full_page=True)
            with open(debug_dir / "500_score.html", "w", encoding="utf-8") as f:
                f.write(await page.content())
            await parse_score(page, match_no, home_team, away_team)

            # 3. 总进球 (playid=270)
            url_270 = f"https://trade.500.com/jczq/?playid=270&g=2&date={match_date}"
            print(f"[500彩票网] 访问总进球页面: {url_270}")
            await fetch_page(page, url_270, wait_time=5000)
            await page.screenshot(path=str(debug_dir / "500_total.png"), full_page=True)
            with open(debug_dir / "500_total.html", "w", encoding="utf-8") as f:
                f.write(await page.content())
            await parse_total_goals(page, match_no, home_team, away_team)

            # 4. 半全场 (playid=272)
            url_272 = f"https://trade.500.com/jczq/?playid=272&g=2&date={match_date}"
            print(f"[500彩票网] 访问半全场页面: {url_272}")
            await fetch_page(page, url_272, wait_time=5000)
            await page.screenshot(path=str(debug_dir / "500_hf.png"), full_page=True)
            with open(debug_dir / "500_hf.html", "w", encoding="utf-8") as f:
                f.write(await page.content())
            await parse_half_full(page, match_no, home_team, away_team)

            await browser.close()
    except Exception as e:
        print(f"[500彩票网] 采集异常: {e}")

    return data
