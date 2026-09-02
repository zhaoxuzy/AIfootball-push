import requests
import re
from src.utils import now_str

def decode_crs(code):
    """解码比分编码"""
    map_special = {"s1sh": "胜其它", "s1sd": "平其它", "s1sa": "负其它"}
    if code in map_special:
        return map_special[code]
    # 格式 s{主队}s{客队}，如 s01s00 -> 1:0
    parts = code[1:].split("s", 1)  # ['01', '00']
    try:
        return f"{int(parts[0])}:{int(parts[1])}"
    except:
        return code  # 未知编码返回原样

def decode_ttg(code):
    """解码总进球"""
    map_goals = {f"s{i}": str(i) for i in range(7)}
    map_goals["s7"] = "7+"
    return map_goals.get(code, code)

def decode_hafu(code):
    """解码半全场编码"""
    mapping = {
        "hh": "胜胜", "hd": "胜平", "ha": "胜负",
        "dh": "平胜", "dd": "平平", "da": "平负",
        "ah": "负胜", "ad": "负平", "aa": "负负"
    }
    return mapping.get(code, code)

def collect_odds_api(match):
    """
    通过竞彩官方API获取全部赔率（使用备用 uniform 端点）。
    返回标准化 dict，缺失字段为 None。
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
    home_team = match.get("home_team", "")
    away_team = match.get("away_team", "")

    # 更换为备用端点
    url = "https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry"

    params = {
        "channel": "c",  # 新增 channel 参数
        "poolCode": "had,hhad,crs,ttg,hafu"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://m.sporttery.cn/mjc/jsq/zqspf/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        api_data = resp.json()
    except Exception as e:
        print(f"[竞彩API] 请求失败: {e}")
        return data

    # 提取比赛列表（兼容不同返回结构）
    match_list = []
    try:
        match_list = api_data["data"]["matchList"]
    except KeyError:
        try:
            match_list = api_data["value"]["matchList"]
        except KeyError:
            print("[竞彩API] 未找到 matchList 字段")
            return data

    # 匹配目标比赛
    target = None
    for m in match_list:
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

    # 1. 胜平负 (had)
    had = target.get("had", {})
    if had:
        h = had.get("h")
        d = had.get("d")
        a = had.get("a")
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

    # 2. 让球胜平负 (hhad)
    hhad = target.get("hhad", {})
    if hhad:
        goal = hhad.get("goal") or hhad.get("rq") or hhad.get("hhadGoal")
        if goal is not None:
            data["让球胜平负"]["官方让球数"] = str(goal)
        h = hhad.get("h")
        d = hhad.get("d")
        a = hhad.get("a")
        if h and d and a:
            data["让球胜平负"]["初赔"]["让胜"] = str(h)
            data["让球胜平负"]["初赔"]["让平"] = str(d)
            data["让球胜平负"]["初赔"]["让负"] = str(a)
            data["让球胜平负"]["即赔"]["让胜"] = str(h)
            data["让球胜平负"]["即赔"]["让平"] = str(d)
            data["让球胜平负"]["即赔"]["让负"] = str(a)

    # 3. 比分赔率 (crs)
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

    # 4. 总进球赔率 (ttg)
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

    # 5. 半全场赔率 (hafu)
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

    # 6. 返还率计算（胜平负）
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
