import asyncio
import re
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from src.utils import now_str

async def collect_odds_api(match):
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

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive"
    }

    def fetch_soup(url):
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            if resp.encoding == "ISO-8859-1":
                resp.encoding = "gb2312"
            elif not resp.encoding:
                resp.encoding = "gb2312"
            return BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            print(f"[500彩票网] 请求失败 {url}: {e}")
            return None

    def find_target_row(soup, match_no, home_team, away_team):
        for tr in soup.find_all("tr"):
            text = tr.get_text(" ", strip=True)
            if match_no in text or home_team in text or away_team in text:
                return tr
        return None

    # ========== 1. 胜平负/让球 ==========
    url_spf = f"https://trade.500.com/jczq/?playid=354&g=2&vtype=nspf&date={match_date}"
    soup_spf = fetch_soup(url_spf)
    if soup_spf:
        tr = find_target_row(soup_spf, match_no, home_team, away_team)
        if tr:
            row_text = tr.get_text(" ", strip=True)
            print(f"[500彩票网] 胜平负/让球行文本: {row_text}")
            # 让球数
            handicap_match = re.search(r"([+-])(\d+)", row_text)
            if handicap_match:
                sign = handicap_match.group(1)
                num = int(handicap_match.group(2))
                data["让球胜平负"]["官方让球数"] = f"{sign}{num}"
            # 提取所有小数
            odds = re.findall(r"\d+\.\d+", row_text)
            print(f"[500彩票网] 小数列表: {odds}")
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
        else:
            print("[500彩票网] 胜平负/让球页面未找到比赛行")

    # ========== 2. 总进球 ==========
    url_total = f"https://trade.500.com/jczq/?playid=270&g=2&date={match_date}"
    soup_total = fetch_soup(url_total)
    if soup_total:
        tr = find_target_row(soup_total, match_no, home_team, away_team)
        if tr:
            row_text = tr.get_text(" ", strip=True)
            print(f"[500彩票网] 总进球行文本: {row_text}")
            odds = re.findall(r"\d+\.\d+", row_text)
            print(f"[500彩票网] 总进球小数列表: {odds}")
            if len(odds) >= 8:
                total_dict = {
                    "0": odds[0], "1": odds[1], "2": odds[2], "3": odds[3],
                    "4": odds[4], "5": odds[5], "6": odds[6], "7+": odds[7]
                }
                data["总进球赔率"] = total_dict
                print("[500彩票网] 已解析总进球赔率")
            else:
                print("[500彩票网] 总进球小数不足8个")
        else:
            print("[500彩票网] 总进球页面未找到比赛行")

    # ========== 3. 半全场 ==========
    url_hf = f"https://trade.500.com/jczq/?playid=272&g=2&date={match_date}"
    soup_hf = fetch_soup(url_hf)
    if soup_hf:
        tr = find_target_row(soup_hf, match_no, home_team, away_team)
        if tr:
            row_text = tr.get_text(" ", strip=True)
            print(f"[500彩票网] 半全场行文本: {row_text}")
            odds = re.findall(r"\d+\.\d+", row_text)
            print(f"[500彩票网] 半全场小数列表: {odds}")
            if len(odds) >= 9:
                options = ["胜胜", "胜平", "胜负", "平胜", "平平", "平负", "负胜", "负平", "负负"]
                hf_dict = {opt: odds[i] for i, opt in enumerate(options)}
                data["半全场赔率"] = hf_dict
                print("[500彩票网] 已解析半全场赔率")
            else:
                print("[500彩票网] 半全场小数不足9个")
        else:
            print("[500彩票网] 半全场页面未找到比赛行")

    # ========== 4. 比分（Playwright 点击展开，固定31项） ==========
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            page.set_default_timeout(120000)

            url_score = f"https://trade.500.com/jczq/?playid=271&g=2&date={match_date}"
            print(f"[500彩票网] 访问比分页面: {url_score}")
            await page.goto(url_score, wait_until="load")
            await page.wait_for_timeout(8000)

            # 定位目标行
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

            if not row_locator:
                print("[500彩票网] 比分页面未定位到比赛行")
                await browser.close()
                return data

            # 点击展开
            try:
                expand_btn = row_locator.locator("button:has-text('展开投注'), a:has-text('展开投注'), span:has-text('展开投注')").first
                if await expand_btn.count() > 0:
                    await expand_btn.click()
                    await page.wait_for_timeout(3000)
                    print("[500彩票网] 已点击比分展开投注")
                else:
                    print("[500彩票网] 未找到展开投注按钮")
            except Exception as e:
                print(f"[500彩票网] 点击展开失败: {e}")

            # 重新获取行文本
            row_text = await row_locator.inner_text()
            print(f"[500彩票网] 比分行文本:\n{row_text}")

            # 提取所有小数
            all_odds = re.findall(r"\d+\.\d+", row_text)
            print(f"[500彩票网] 比分小数数量: {len(all_odds)}")

            # 固定顺序映射（31项）
            if len(all_odds) >= 31:
                home_keys = ["1:0","2:0","2:1","3:0","3:1","3:2","4:0","4:1","4:2","5:0","5:1","5:2","胜其它"]
                draw_keys = ["0:0","1:1","2:2","3:3","平其它"]
                away_keys = ["0:1","0:2","1:2","0:3","1:3","2:3","0:4","1:4","2:4","0:5","1:5","2:5","负其它"]
                all_keys = home_keys + draw_keys + away_keys
                score_dict = {k: v for k, v in zip(all_keys, all_odds)}
                data["比分赔率"] = score_dict
                print("[500彩票网] 已按固定顺序映射比分赔率")
            else:
                # 备用：按文本匹配
                pairs = re.findall(r"(\d+[:：]\d+)\s+(\d+\.\d+)", row_text)
                if pairs:
                    score_dict = {}
                    for score, odds in pairs:
                        score_clean = score.replace(":", "-").replace("：", "-")
                        score_dict[score_clean] = odds
                    data["比分赔率"] = score_dict
                    print(f"[500彩票网] 备用匹配到比分赔率 {len(score_dict)} 项")
                else:
                    print("[500彩票网] 未匹配到比分赔率")

            await browser.close()
    except Exception as e:
        print(f"[500彩票网] 比分解析异常: {e}")

    # ========== 返还率计算 ==========
    try:
        h = float(data["胜平负"]["即赔"]["主胜"])
        d = float(data["胜平负"]["即赔"]["平"])
        a = float(data["胜平负"]["即赔"]["客胜"])
        if h and d and a:
            calc = 1 / (1/h + 1/d + 1/a)
            data["返还率"]["胜平负返还率"] = f"{calc*100:.2f}% (计算值)"
    except:
        pass

    return data
