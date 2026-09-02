import asyncio
import re
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from src.utils import now_str

async def collect_odds_api(match):
    """
    混合采集竞彩赔率：
    1. 胜平负/让球：500彩票网直接解析
    2. 总进球/半全场/比分：竞彩官网 Playwright 模拟点击标签
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

    # 清洗队名
    if " " in home_team:
        home_team = home_team.strip().split()[-1]
    if " " in away_team:
        away_team = away_team.strip().split()[-1]

    # ========== 第一部分：500彩票网解析胜平负/让球 ==========
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

    # 胜平负/让球页面
    url_spf = f"https://trade.500.com/jczq/?playid=354&g=2&vtype=nspf&date={match_date}"
    soup_spf = fetch_soup(url_spf)
    if soup_spf:
        tr = find_target_row(soup_spf, match_no, home_team, away_team)
        if tr:
            row_text = tr.get_text(" ", strip=True)
            print(f"[500彩票网] 胜平负/让球行文本: {row_text}")
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
        else:
            print("[500彩票网] 胜平负/让球页面未找到比赛行")

    # 返还率计算（胜平负）
    try:
        h = float(data["胜平负"]["即赔"]["主胜"])
        d = float(data["胜平负"]["即赔"]["平"])
        a = float(data["胜平负"]["即赔"]["客胜"])
        if h and d and a:
            calc = 1 / (1/h + 1/d + 1/a)
            data["返还率"]["胜平负返还率"] = f"{calc*100:.2f}% (计算值)"
    except:
        pass

    # ========== 第二部分：竞彩官网 Playwright 获取总进球/半全场/比分 ==========
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            page.set_default_timeout(90000)  # 90秒超时

            # 打开竞彩官网移动版
            url = "https://m.sporttery.cn/mjc/jsq/zqspf/"
            print(f"[竞彩官网] 打开页面: {url}")
            await page.goto(url, wait_until="load")
            await page.wait_for_timeout(5000)

            # 辅助函数：在当前页面查找目标比赛行
            async def find_row_on_page():
                # 优先按编号
                locator = page.locator(f"text={match_no}").first
                if await locator.count() > 0:
                    return locator.locator("xpath=ancestor::tr[1]")
                # 按主队
                locator = page.locator(f"text={home_team}").first
                if await locator.count() > 0:
                    return locator.locator("xpath=ancestor::tr[1]")
                # 按客队
                locator = page.locator(f"text={away_team}").first
                if await locator.count() > 0:
                    return locator.locator("xpath=ancestor::tr[1]")
                return None

            # 1. 总进球（进球数标签）
            print("[竞彩官网] 点击'进球数'标签")
            try:
                await page.click("text=进球数", timeout=15000)
                await page.wait_for_selector("table tbody tr", timeout=15000)
                await page.wait_for_timeout(2000)
                row = await find_row_on_page()
                if row:
                    cells = await row.locator("td").all_text_contents()
                    print(f"[竞彩官网] 总进球行单元格: {cells}")
                    # 假设赔率从第5个单元格开始（索引4），共8个
                    if len(cells) >= 12:
                        odds = cells[4:12]
                        odds = [re.sub(r"[^\d.]", "", o) for o in odds]
                        if all(re.match(r"\d+\.\d+", o) for o in odds):
                            total_dict = {
                                "0": odds[0], "1": odds[1], "2": odds[2], "3": odds[3],
                                "4": odds[4], "5": odds[5], "6": odds[6], "7+": odds[7]
                            }
                            data["总进球赔率"] = total_dict
                            print("[竞彩官网] 已获取总进球赔率")
                else:
                    print("[竞彩官网] 总进球页面未找到比赛行")
            except Exception as e:
                print(f"[竞彩官网] 总进球提取失败: {e}")

            # 2. 半全场
            print("[竞彩官网] 点击'半全场'标签")
            try:
                await page.click("text=半全场", timeout=15000)
                await page.wait_for_selector("table tbody tr", timeout=15000)
                await page.wait_for_timeout(2000)
                row = await find_row_on_page()
                if row:
                    cells = await row.locator("td").all_text_contents()
                    print(f"[竞彩官网] 半全场行单元格: {cells}")
                    if len(cells) >= 13:
                        odds = cells[4:13]  # 9个赔率
                        odds = [re.sub(r"[^\d.]", "", o) for o in odds]
                        if all(re.match(r"\d+\.\d+", o) for o in odds):
                            options = ["胜胜", "胜平", "胜负", "平胜", "平平", "平负", "负胜", "负平", "负负"]
                            hf_dict = {opt: odds[i] for i, opt in enumerate(options)}
                            data["半全场赔率"] = hf_dict
                            print("[竞彩官网] 已获取半全场赔率")
                else:
                    print("[竞彩官网] 半全场页面未找到比赛行")
            except Exception as e:
                print(f"[竞彩官网] 半全场提取失败: {e}")

            # 3. 比分
            print("[竞彩官网] 点击'比分'标签")
            try:
                await page.click("text=比分", timeout=15000)
                await page.wait_for_selector("table tbody tr", timeout=15000)
                await page.wait_for_timeout(3000)
                row = await find_row_on_page()
                if row:
                    # 比分数据可能在行内展开，尝试获取行内所有文本
                    row_text = await row.inner_text()
                    print(f"[竞彩官网] 比分行文本: {row_text}")
                    # 提取比分和赔率对
                    pairs = re.findall(r"(\d+[:：]\d+)\s+(\d+\.\d+)", row_text)
                    if pairs:
                        score_dict = {}
                        for score, odds in pairs:
                            score_clean = score.replace(":", "-").replace("：", "-")
                            score_dict[score_clean] = odds
                        data["比分赔率"] = score_dict
                        print(f"[竞彩官网] 已获取比分赔率 {len(score_dict)} 项")
                    else:
                        print("[竞彩官网] 未匹配到比分赔率格式")
                else:
                    print("[竞彩官网] 比分页面未找到比赛行")
            except Exception as e:
                print(f"[竞彩官网] 比分提取失败: {e}")

            await browser.close()
    except Exception as e:
        print(f"[竞彩官网] Playwright 执行异常: {e}")

    return data
