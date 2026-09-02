import requests
import re
from bs4 import BeautifulSoup
from src.utils import now_str

def collect_odds_api(match):
    """
    通过500彩票网页面直接解析竞彩赔率（requests + BeautifulSoup）。
    返回标准化 dict，缺失字段为 None。
    注意：比分赔率因需要点击展开，暂不实现，后续可单独用 Playwright 补充。
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
        """请求页面并返回BeautifulSoup对象，编码自动处理"""
        try:
            resp = requests.get(url, headers=headers, timeout=15)
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
        """在表格中查找目标比赛行，返回tr标签"""
        for tr in soup.find_all("tr"):
            text = tr.get_text(" ", strip=True)
            if match_no in text or home_team in text or away_team in text:
                return tr
        return None

    # 1. 胜平负/让球胜平负页面 (playid=354&vtype=nspf)
    url_spf = f"https://trade.500.com/jczq/?playid=354&g=2&vtype=nspf&date={match_date}"
    soup_spf = fetch_soup(url_spf)
    if soup_spf:
        tr = find_target_row(soup_spf, match_no, home_team, away_team)
        if tr:
            row_text = tr.get_text(" ", strip=True)
            print(f"[500彩票网] 胜平负/让球行文本: {row_text}")
            # 让球数（+1 或 -1）
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

    # 2. 总进球页面 (playid=270)
    url_total = f"https://trade.500.com/jczq/?playid=270&g=2&date={match_date}"
    soup_total = fetch_soup(url_total)
    if soup_total:
        tr = find_target_row(soup_total, match_no, home_team, away_team)
        if tr:
            row_text = tr.get_text(" ", strip=True)
            print(f"[500彩票网] 总进球行文本: {row_text}")
            # 提取数字对：0 27.00, 1 7.00, ... 7+ 18.00
            # 兼容无空格形式：027.00 -> 0 27.00
            # 使用更宽泛的匹配
            text_clean = re.sub(r"\s+", " ", row_text)  # 合并空格
            # 先提取所有小数
            all_odds = re.findall(r"\d+\.\d+", text_clean)
            # 提取所有整数标签（0-7+）
            goal_labels = re.findall(r"(?<!\d)(\d\+?)(?=\s*\d+\.\d+)", text_clean)
            if len(all_odds) >= 8 and len(goal_labels) >= 8:
                total_dict = {}
                for i in range(8):
                    total_dict[goal_labels[i]] = all_odds[i]
                data["总进球赔率"] = total_dict
                print(f"[500彩票网] 已解析总进球赔率 {len(total_dict)} 项")
            else:
                print("[500彩票网] 总进球赔率解析不完整")
        else:
            print("[500彩票网] 总进球页面未找到比赛行")

    # 3. 半全场页面 (playid=272)
    url_hf = f"https://trade.500.com/jczq/?playid=272&g=2&date={match_date}"
    soup_hf = fetch_soup(url_hf)
    if soup_hf:
        tr = find_target_row(soup_hf, match_no, home_team, away_team)
        if tr:
            row_text = tr.get_text(" ", strip=True)
            print(f"[500彩票网] 半全场行文本: {row_text}")
            all_odds = re.findall(r"\d+\.\d+", row_text)
            if len(all_odds) >= 9:
                options = ["胜胜", "胜平", "胜负", "平胜", "平平", "平负", "负胜", "负平", "负负"]
                hf_dict = {opt: all_odds[i] for i, opt in enumerate(options)}
                data["半全场赔率"] = hf_dict
                print(f"[500彩票网] 已解析半全场赔率 {len(hf_dict)} 项")
            else:
                print("[500彩票网] 半全场赔率不足9个，未解析")
        else:
            print("[500彩票网] 半全场页面未找到比赛行")

    # 4. 比分赔率 (playid=271) - 需要点击展开，此版本不处理，暂保持 None

    # 5. 返还率计算（胜平负）
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
