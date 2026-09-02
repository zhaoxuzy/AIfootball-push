import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from src.utils import now_str

async def collect_500_odds(match):
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

    match_no = match.get("match_no", "")
    match_date = match.get("match_date", "")
    home_team = match.get("home_team", "")
    away_team = match.get("away_team", "")

    # 清洗队名
    if " " in home_team:
        home_team = home_team.strip().split()[-1]
    if " " in away_team:
        away_team = away_team.strip().split()[-1]

    debug_dir = Path("output/debug_500")
    debug_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_page(page, url, prefix):
        """访问页面，带重试，超时60秒"""
        for attempt in range(2):
            try:
                print(f"[500彩票网] 尝试第 {attempt+1} 次访问: {url}")
                await page.goto(url, wait_until="load", timeout=60000)
                await page.wait_for_timeout(5000)  # 额外等待动态渲染
                # 成功则保存文件
                await page.screenshot(path=str(debug_dir / f"{prefix}.png"), full_page=True)
                with open(debug_dir / f"{prefix}.html", "w", encoding="utf-8") as f:
                    f.write(await page.content())
                return BeautifulSoup(await page.content(), "lxml")
            except Exception as e:
                print(f"[500彩票网] 第 {attempt+1} 次访问失败: {e}")
                if attempt == 1:
                    return None
                await page.wait_for_timeout(3000)

    def find_target_row(soup, match_no, home_team, away_team):
        for tr in soup.find_all("tr"):
            text = tr.get_text(" ", strip=True)
            if match_no in text or home_team in text or away_team in text:
                return tr
        return None

    async def parse_spf_rqspf(page):
        url = f"https://trade.500.com/jczq/?playid=354&g=2&vtype=nspf&date={match_date}"
        soup = await fetch_page(page, url, "spf")
        if not soup:
            print("[500彩票网] 胜平负/让球页面获取失败")
            return

        tr = find_target_row(soup, match_no, home_team, away_team)
        if not tr:
            print("[500彩票网] 胜平负/让球页面未找到比赛行")
            return

        row_text = tr.get_text(" ", strip=True)
        print(f"[500彩票网] 胜平负/让球行文本:\n{row_text}")

        handicap_match = re.search(r"([+-])(\d+)", row_text)
        if handicap_match:
            sign = handicap_match.group(1)
            num = int(handicap_match.group(2))
            data["让球胜平负"]["官方让球数"] = f"{sign}{num}"

        odds = re.findall(r"\d+\.\d+", row_text)
        print(f"[500彩票网] 小数赔率列表: {odds}")

        if len(odds) >= 3:
            h, d, a = odds[0], odds[1], odds[2]
            data["胜平负"]["初赔"]["主胜"] = h
            data["胜平负"]["初赔"]["平"] = d
            data["胜平负"]["初赔"]["客胜"] = a
            data["胜平负"]["即赔"]["主胜"] = h
            data["胜平负"]["即赔"]["平"] = d
            data["胜平负"]["即赔"]["客胜"] = a
        if len(odds) >= 6:
            rh, rd, ra = odds[3], odds[4], odds[5]
            data["让球胜平负"]["初赔"]["让胜"] = rh
            data["让球胜平负"]["初赔"]["让平"] = rd
            data["让球胜平负"]["初赔"]["让负"] = ra
            data["让球胜平负"]["即赔"]["让胜"] = rh
            data["让球胜平负"]["即赔"]["让平"] = rd
            data["让球胜平负"]["即赔"]["让负"] = ra

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            page.set_default_timeout(60000)  # 默认60秒超时

            await parse_spf_rqspf(page)

            await browser.close()
    except Exception as e:
        print(f"[500彩票网] 采集异常: {e}")

    return data
