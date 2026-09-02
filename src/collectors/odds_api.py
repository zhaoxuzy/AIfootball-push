import re
import json
from playwright.async_api import async_playwright
from src.utils import now_str

def decode_crs(code):
    map_special = {"s1sh": "胜其它", "s1sd": "平其它", "s1sa": "负其它"}
    if code in map_special:
        return map_special[code]
    parts = code[1:].split("s", 1)
    try:
        return f"{int(parts[0])}:{int(parts[1])}"
    except:
        return code

def decode_ttg(code):
    map_goals = {f"s{i}": str(i) for i in range(7)}
    map_goals["s7"] = "7+"
    return map_goals.get(code, code)

def decode_hafu(code):
    mapping = {
        "hh": "胜胜", "hd": "胜平", "ha": "胜负",
        "dh": "平胜", "dd": "平平", "da": "平负",
        "ah": "负胜", "ad": "负平", "aa": "负负"
    }
    return mapping.get(code, code)

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
    home_team = match.get("home_team", "")
    away_team = match.get("away_team", "")

    captured_responses = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            page.set_default_timeout(60000)

            # 监听网络响应
            async def handle_response(response):
                if "getMatchCalculatorV1.qry" in response.url:
                    try:
                        body = await response.json()
                        captured_responses.append(body)
                        print(f"[竞彩API] 捕获到响应，长度: {len(json.dumps(body))}")
                    except Exception as e:
                        print(f"[竞彩API] 解析响应失败: {e}")

            page.on("response", handle_response)

            # 打开页面
            url = "https://m.sporttery.cn/mjc/jsq/zqspf/"
            print(f"[竞彩API] 打开页面: {url}")
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(5000)

            # 如果没有捕获到数据，尝试点击其他玩法标签
            if not captured_responses:
                print("[竞彩API] 未捕获到数据，尝试点击比分、进球数、半全场标签")
                tabs = ["比分", "进球数", "半全场"]
                for tab in tabs:
                    try:
                        await page.click(f"text={tab}")
                        await page.wait_for_timeout(2000)
                        if captured_responses:
                            break
                    except Exception as e:
                        print(f"[竞彩API] 点击 {tab} 失败: {e}")

            await browser.close()
    except Exception as e:
        print(f"[竞彩API] Playwright 执行异常: {e}")
        return data

    if not captured_responses:
        print("[竞彩API] 未捕获到任何API响应")
        return data

    # 合并所有响应中的 matchList
    all_matches = []
    for resp in captured_responses:
        try:
            match_list = resp.get("data", {}).get("matchList", [])
            if not match_list:
                match_list = resp.get("value", {}).get("matchList", [])
            all_matches.extend(match_list)
        except:
            pass

    if not all_matches:
        print("[竞彩API] 响应中未找到 matchList")
        return data

    # 匹配目标比赛
    target = None
    for m in all_matches:
        if m.get("matchNumStr") == match_no or m.get("matchNum") == match_no:
            target = m
            break
        if (m.get("homeTeam") == home_team or home_team in m.get("homeTeam", "")) and \
           (m.get("awayTeam") == away_team or away_team in m.get("awayTeam", "")):
            target = m
            break

    if not target:
        print(f"[竞彩API] 未找到比赛 {match_no} {home_team} VS {away_team}")
        return data

    # 解析各玩法赔率（同之前版本）
    had = target.get("had", {})
    if had:
        h, d, a = had.get("h"), had.get("d"), had.get("a")
        if h and d and a:
            data["胜平负"]["初赔"]["主胜"] = str(h)
            data["胜平负"]["初赔"]["平"] = str(d)
            data["胜平负"]["初赔"]["客胜"] = str(a)
            data["胜平负"]["即赔"]["主胜"] = str(h)
            data["胜平负"]["即赔"]["平"] = str(d)
            data["胜平负"]["即赔"]["客胜"] = str(a)
            t = had.get("updateTime") or had.get("updateDate")
            if t:
                data["胜平负"]["初赔"]["时间"] = t
                data["胜平负"]["即赔"]["时间"] = t
        single = had.get("single")
        if single is not None:
            data["是否单关"] = bool(single)

    hhad = target.get("hhad", {})
    if hhad:
        goal = hhad.get("goal") or hhad.get("rq") or hhad.get("hhadGoal")
        if goal is not None:
            data["让球胜平负"]["官方让球数"] = str(goal)
        h, d, a = hhad.get("h"), hhad.get("d"), hhad.get("a")
        if h and d and a:
            data["让球胜平负"]["初赔"]["让胜"] = str(h)
            data["让球胜平负"]["初赔"]["让平"] = str(d)
            data["让球胜平负"]["初赔"]["让负"] = str(a)
            data["让球胜平负"]["即赔"]["让胜"] = str(h)
            data["让球胜平负"]["即赔"]["让平"] = str(d)
            data["让球胜平负"]["即赔"]["让负"] = str(a)

    crs = target.get("crs", {})
    if crs:
        score_dict = {}
        for code, odds in crs.items():
            if code in ("updateDate", "updateTime"):
                continue
            score = decode_crs(code)
            score_dict[score] = str(odds)
        if score_dict:
            data["比分赔率"] = score_dict

    ttg = target.get("ttg", {})
    if ttg:
        total_dict = {}
        for code, odds in ttg.items():
            if code in ("updateDate", "updateTime"):
                continue
            goals = decode_ttg(code)
            total_dict[goals] = str(odds)
        if total_dict:
            data["总进球赔率"] = total_dict

    hafu = target.get("hafu", {})
    if hafu:
        hf_dict = {}
        for code, odds in hafu.items():
            if code in ("updateDate", "updateTime"):
                continue
            key = decode_hafu(code)
            hf_dict[key] = str(odds)
        if hf_dict:
            data["半全场赔率"] = hf_dict

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
