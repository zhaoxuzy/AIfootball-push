import asyncio
import re
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from src.utils import now_str

async def collect_odds_api(match):
    """
    全部使用500彩票网采集竞彩赔率。
    胜平负/让球：requests直接解析。
    总进球、半全场：requests解析td单元格。
    比分：Playwright异步点击展开后解析。
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

    match_no = match.get("match_no", "")
    match_date = match.get("match_date", "")
    home_team = match.get("home_team", "")
    away_team = match.get("away_team", "")

    # 清洗队名（可能包含联赛前缀）
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
        """请求页面并返回 BeautifulSoup 对象"""
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            # 500彩票网通常使用GBK编码
            if resp.encoding == "ISO-8859-1":
                resp.encoding = "gb2312"
            elif not resp.encoding:
                resp.encoding = "gb2312"
            return BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            print(f"[500彩票网] 请求失败 {url}: {e}")
            return None

    def find_target_row(soup, match_no, home_team, away_team):
        """在表格中查找目标比赛行"""
        for tr in soup.find_all("tr"):
            text = tr.get_text(" ", strip=True)
            if match_no in text or home_team in text or away_team in text:
                return tr
        return None

    # ========== 1. 胜平负/让球 (playid=354&vtype=nspf) ==========
    url_spf = f"https://trade.500.com/jczq/?playid=354&g=2&vtype=nspf&date={match_date}"
    soup_spf = fetch_soup(url_spf)
    if soup_spf:
        tr = find_target_row(soup_spf, match_no, home_team, away_team)
        if tr:
            row_text = tr.get_text(" ", strip=True)
            print(f"[500彩票网] 胜平负/让球行文本: {row_text}")

            # 提取让球数
            handicap_match = re.search(r"([+-])(\d+)", row_text)
            if handicap_match:
                sign = handicap_match.group(1)
                num = int(handicap_match.group(2))
                data["让球胜平负"]["官方让球数"] = f"{sign}{num}"

            # 提取所有小数赔率
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
        else:
            print("[500彩票网] 胜平负/让球页面未找到比赛行")

    # ========== 2. 总进球 (playid=270) ==========
    url_total = f"https://trade.500.com/jczq/?playid=270&g=2&date={match_date}"
    soup_total = fetch_soup(url_total)
    if soup_total:
        tr = find_target_row(soup_total, match_no, home_team, away_team)
        if tr:
            tds = tr.find_all("td")
            # 打印所有 td 内容，便于调试
            td_texts = [td.get_text(strip=True) for td in tds]
            print(f"[500彩票网] 总进球行所有单元格: {td_texts}")

            # 根据页面结构，赔率从第5个td开始（索引4），共8个
            if len(tds) >= 12:
                odds = [td.get_text(strip=True) for td in tds[4:12]]
                # 去除可能的箭头等非数字字符
                odds = [re.sub(r"[^\d.]", "", o) for o in odds]
                if all(re.match(r"\d+\.\d+", o) for o in odds):
                    total_dict = {
                        "0": odds[0], "1": odds[1], "2": odds[2], "3": odds[3],
                        "4": odds[4], "5": odds[5], "6": odds[6], "7+": odds[7]
                    }
                    data["总进球赔率"] = total_dict
                    print("[500彩票网] 已解析总进球赔率")
                else:
                    print("[500彩票网] 总进球赔率单元格格式异常")
            else:
                print("[500彩票网] 总进球行 td 数量不足")
        else:
            print("[500彩票网] 总进球页面未找到比赛行")

    # ========== 3. 半全场 (playid=272) ==========
    url_hf = f"https://trade.500.com/jczq/?playid=272&g=2&date={match_date}"
    soup_hf = fetch_soup(url_hf)
    if soup_hf:
        tr = find_target_row(soup_hf, match_no, home_team, away_team)
        if tr:
            tds = tr.find_all("td")
            td_texts = [td.get_text(strip=True) for td in tds]
            print(f"[500彩票网] 半全场行所有单元格: {td_texts}")

            # 赔率从第5个td开始，共9个
            if len(tds) >= 14:
                odds = [td.get_text(strip=True) for td in tds[4:13]]
                odds = [re.sub(r"[^\d.]", "", o) for o in odds]
                if all(re.match(r"\d+\.\d+", o) for o in odds):
                    options = ["胜胜", "胜平", "胜负", "平胜", "平平", "平负", "负胜", "负平", "负负"]
                    hf_dict = {opt: odds[i] for i, opt in enumerate(options)}
                    data["半全场赔率"] = hf_dict
                    print("[500彩票网] 已解析半全场赔率")
                else:
                    print("[500彩票网] 半全场赔率单元格格式异常")
            else:
                print("[500彩票网] 半全场行 td 数量不足")
        else:
            print("[500彩票网] 半全场页面未找到比赛行")

    # ========== 4. 比分 (playid=271) - 使用 Playwright 点击展开 ==========
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            page.set_default_timeout(120000)  # 120秒超时

            url_score = f"https://trade.500.com/jczq/?playid=271&g=2&date={match_date}"
            print(f"[500彩票网] 访问比分页面: {url_score}")
            await page.goto(url_score, wait_until="load")
            await page.wait_for_timeout(8000)  # 额外等待页面渲染

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

            # 点击展开投注按钮
            try:
                expand_btn = row_locator.locator("button:has-text('展开投注'), a:has-text('展开投注'), span:has-text('展开投注')").first
                if await expand_btn.count() > 0:
                    await expand_btn.click()
                    await page.wait_for_timeout(3000)
                    print("[500彩票网] 已点击比分展开投注")
                else:
                    print("[500彩票网] 未找到展开投注按钮")
            except Exception as e:
                print(f"[500彩票网] 点击展开投注失败: {e}")

            # 重新获取行文本，提取比分赔率
            row_text = await row_locator.inner_text()
            print(f"[500彩票网] 比分行文本:\n{row_text}")

            # 提取比分和赔率对，如 "1:0 11.5"
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

            await browser.close()
    except Exception as e:
        print(f"[500彩票网] 比分解析异常: {e}")

    # ========== 返还率计算（胜平负） ==========
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
