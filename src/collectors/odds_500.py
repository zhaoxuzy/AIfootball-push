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

    # 清洗队名（可能包含联赛前缀）
    if " " in home_team:
        home_team = home_team.strip().split()[-1]
    if " " in away_team:
        away_team = away_team.strip().split()[-1]

    debug_dir = Path("output/debug_500")
    debug_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_page(page, url, prefix):
        """访问页面，带重试，超时60秒，返回BeautifulSoup对象"""
        for attempt in range(2):
            try:
                print(f"[500彩票网] 尝试第 {attempt+1} 次访问: {url}")
                await page.goto(url, wait_until="load", timeout=60000)
                await page.wait_for_timeout(5000)  # 额外等待动态渲染
                await page.screenshot(path=str(debug_dir / f"{prefix}.png"), full_page=True)
                with open(debug_dir / f"{prefix}.html", "w", encoding="utf-8") as f:
                    f.write(await page.content())
                return BeautifulSoup(await page.content(), "lxml")
            except Exception as e:
                print(f"[500彩票网] 第 {attempt+1} 次访问失败: {e}")
                if attempt == 1:
                    return None
                await page.wait_for_timeout(3000)
        return None

    def find_target_row(soup, match_no, home_team, away_team):
        """在表格中查找目标比赛行，返回tr标签"""
        for tr in soup.find_all("tr"):
            text = tr.get_text(" ", strip=True)
            if match_no in text or home_team in text or away_team in text:
                return tr
        return None

    async def parse_spf_rqspf(page):
        """解析胜平负/让球胜平负"""
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

        # 提取让球数
        handicap_match = re.search(r"([+-])(\d+)", row_text)
        if handicap_match:
            sign = handicap_match.group(1)
            num = int(handicap_match.group(2))
            data["让球胜平负"]["官方让球数"] = f"{sign}{num}"

        # 提取所有小数（即时赔率）
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
            print("[500彩票网] 已填充胜平负初赔/即赔")
        if len(odds) >= 6:
            rh, rd, ra = odds[3], odds[4], odds[5]
            data["让球胜平负"]["初赔"]["让胜"] = rh
            data["让球胜平负"]["初赔"]["让平"] = rd
            data["让球胜平负"]["初赔"]["让负"] = ra
            data["让球胜平负"]["即赔"]["让胜"] = rh
            data["让球胜平负"]["即赔"]["让平"] = rd
            data["让球胜平负"]["即赔"]["让负"] = ra
            print("[500彩票网] 已填充让球胜平负初赔/即赔")
        else:
            print("[500彩票网] 赔率数量不足6个，让球赔率未填充")

    async def parse_total_goals(page):
        """解析总进球赔率"""
        url = f"https://trade.500.com/jczq/?playid=270&g=2&date={match_date}"
        soup = await fetch_page(page, url, "total")
        if not soup:
            print("[500彩票网] 总进球页面获取失败")
            return

        tr = find_target_row(soup, match_no, home_team, away_team)
        if not tr:
            print("[500彩票网] 总进球页面未找到比赛行")
            return

        row_text = tr.get_text(" ", strip=True)
        print(f"[500彩票网] 总进球行文本:\n{row_text}")

        # 匹配 (0 6.50) (1 4.20) ... (7+ 18.00)
        pairs = re.findall(r"(\d\+?)\s+(\d+\.\d+)", row_text)
        if pairs:
            total_dict = {k: v for k, v in pairs}
            data["总进球赔率"] = total_dict
            print(f"[500彩票网] 已解析总进球赔率 {len(total_dict)} 项")
        else:
            print("[500彩票网] 未匹配到总进球赔率格式")

    async def parse_half_full(page):
        """解析半全场赔率"""
        url = f"https://trade.500.com/jczq/?playid=272&g=2&date={match_date}"
        soup = await fetch_page(page, url, "hf")
        if not soup:
            print("[500彩票网] 半全场页面获取失败")
            return

        tr = find_target_row(soup, match_no, home_team, away_team)
        if not tr:
            print("[500彩票网] 半全场页面未找到比赛行")
            return

        row_text = tr.get_text(" ", strip=True)
        print(f"[500彩票网] 半全场行文本:\n{row_text}")

        # 提取所有小数，按顺序分配给9项
        odds = re.findall(r"\d+\.\d+", row_text)
        if len(odds) >= 9:
            options = ["胜胜", "胜平", "胜负", "平胜", "平平", "平负", "负胜", "负平", "负负"]
            hf_dict = {opt: odds[i] for i, opt in enumerate(options)}
            data["半全场赔率"] = hf_dict
            print(f"[500彩票网] 已解析半全场赔率 {len(hf_dict)} 项")
        else:
            print("[500彩票网] 半全场赔率不足9个，未解析")

    async def parse_score(page):
        """解析比分赔率（需点击展开投注）"""
        url = f"https://trade.500.com/jczq/?playid=271&g=2&date={match_date}"
        # 直接使用 page 访问，以便点击按钮
        try:
            await page.goto(url, wait_until="load", timeout=60000)
            await page.wait_for_timeout(5000)

            # 定位目标行（Playwright）
            row_locator = None
            locator = page.locator(f"text={match_no}").first
            if await locator.count() > 0:
                row_locator = locator.locator("xpath=ancestor::tr[1]")
            else:
                for team in [home_team, away_team]:
                    locator = page.locator(f"text={team}").first
                    if await locator.count() > 0:
                        row_locator = locator.locator("xpath=ancestor::tr[1]")
                        break

            if row_locator:
                # 查找并点击行内“展开投注”按钮
                expand_btn = row_locator.locator("button:has-text('展开投注'), a:has-text('展开投注'), span:has-text('展开投注')").first
                if await expand_btn.count() > 0:
                    await expand_btn.click()
                    await page.wait_for_timeout(2000)
                    print("[500彩票网] 已点击比分行展开投注")
                else:
                    print("[500彩票网] 行内未找到展开投注按钮，尝试全局查找")
                    expand_btn = page.locator("button:has-text('展开投注'), a:has-text('展开投注'), span:has-text('展开投注')").first
                    if await expand_btn.count() > 0:
                        await expand_btn.click()
                        await page.wait_for_timeout(2000)
                        print("[500彩票网] 已点击全局展开投注按钮")
            else:
                print("[500彩票网] 比分页面未定位到比赛行，无法点击展开")
                return

            # 重新获取页面HTML并解析
            soup = BeautifulSoup(await page.content(), "lxml")
            tr = find_target_row(soup, match_no, home_team, away_team)
            if not tr:
                print("[500彩票网] 比分页面未找到比赛行")
                return

            row_text = tr.get_text(" ", strip=True)
            print(f"[500彩票网] 比分行文本:\n{row_text}")

            # 提取比分和赔率对，格式如 "1:0 11.5"
            pairs = re.findall(r"(\d+[:：]\d+)\s+(\d+\.\d+)", row_text)
            if pairs:
                score_dict = {}
                for score, odds in pairs:
                    score_clean = score.replace(":", "-").replace("：", "-")
                    score_dict[score_clean] = odds
                data["比分赔率"] = score_dict
                print(f"[500彩票网] 已解析比分赔率 {len(score_dict)} 项")
            else:
                print("[500彩票网] 未匹配到比分赔率格式")

        except Exception as e:
            print(f"[500彩票网] 比分解析异常: {e}")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            page.set_default_timeout(60000)  # 默认60秒超时

            # 1. 胜平负/让球
            await parse_spf_rqspf(page)

            # 2. 总进球
            await parse_total_goals(page)

            # 3. 半全场
            await parse_half_full(page)

            # 4. 比分（需要点击，放在最后避免影响其他页面的soup）
            await parse_score(page)

            await browser.close()
    except Exception as e:
        print(f"[500彩票网] 采集异常: {e}")

    return data
