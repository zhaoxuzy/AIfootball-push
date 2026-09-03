import pandas as pd
from src.utils import fetch_url, fetch_json, now_str
from src.config import LEAGUE_KEY_MAP
from src.team_mapper import get_sofascore_team_id

def collect_elo(team_en: str):
    """从ClubElo获取Elo评分"""
    csv_url = "https://www.clubelo.com/ClubElo"
    content = fetch_url(csv_url)
    if content:
        lines = content.splitlines()
        for line in lines[1:]:
            parts = line.split(',')
            if len(parts) >= 3 and parts[1].lower() == team_en.lower():
                try:
                    return {"评分": float(parts[2]), "来源": "ClubElo", "更新时间": now_str()}
                except:
                    pass
    return {"评分": None, "来源": "ClubElo", "更新时间": now_str()}

def collect_xg(team_en: str, league_key: str, season: str):
    """从fbref获取赛季xG/xGA"""
    if not league_key or not team_en:
        return {"赛季xG": None, "赛季xGA": None}
    url = f"https://fbref.com/en/comps/{league_key}/{season}/stats/{season}-{league_key}-Stats"
    try:
        tables = pd.read_html(url)
        if tables:
            df = tables[0]
            squad_col = None
            xg_col = None
            xga_col = None
            for col in df.columns:
                if 'Squad' in col or 'Team' in col:
                    squad_col = col
                if 'xG' in col and 'xGA' not in col:
                    xg_col = col
                if 'xGA' in col:
                    xga_col = col
            if squad_col and xg_col and xga_col:
                row = df[df[squad_col].str.contains(team_en, case=False, na=False)]
                if not row.empty:
                    xg = float(row.iloc[0][xg_col])
                    xga = float(row.iloc[0][xga_col])
                    return {"赛季xG": xg, "赛季xGA": xga}
    except Exception as e:
        print(f"xG采集失败: {e}")
    return {"赛季xG": None, "赛季xGA": None}

def collect_recent_form(team_en: str, league_key: str, season: str):
    """近5场战绩"""
    team_id = get_sofascore_team_id(team_en)
    if not team_id:
        return {"近5场": []}
    url = f"https://api.sofascore.com/api/v1/team/{team_id}/schedule"
    data = fetch_json(url)
    recent = []
    if data and 'events' in data:
        for ev in data['events'][:5]:
            home = ev['homeTeam']['name']
            away = ev['awayTeam']['name']
            score = f"{ev.get('homeScore', 0)}-{ev.get('awayScore', 0)}"
            recent.append({
                "对手": away if home == team_en else home,
                "主客": "主" if home == team_en else "客",
                "比分": score,
                "赛事": ev.get('tournament', {}).get('name', ''),
                "日期": ev.get('startTimestamp', '')
            })
    return {"近5场": recent}

def collect_injuries(team_en: str):
    """伤停（简化版，实际可爬取Transfermarkt）"""
    return {"伤停名单": [], "伤停信息完整度": "低", "来源": "未采集"}

def collect_coach_info(team_en: str):
    """主教练"""
    team_id = get_sofascore_team_id(team_en)
    if team_id:
        url = f"https://api.sofascore.com/api/v1/team/{team_id}"
        data = fetch_json(url)
        if data and 'coach' in data:
            coach = data['coach']
            return {"姓名": coach.get('name'), "上任时间": None, "执教风格": None}
    return {"姓名": None, "上任时间": None, "执教风格": None}

def collect_head_to_head(home_en: str, away_en: str):
    """历史交锋"""
    search_url = f"https://api.sofascore.com/api/v1/search?q={home_en.replace(' ', '%20')}%20{away_en.replace(' ', '%20')}"
    data = fetch_json(search_url)
    h2h = []
    if data and 'results' in data:
        events = [r for r in data['results'] if r['type'] == 'event'][:5]
        for ev in events:
            h2h.append({
                "日期": ev.get('startTimestamp', ''),
                "赛事": ev.get('tournament', {}).get('name', ''),
                "主队": ev.get('homeTeam', {}).get('name', ''),
                "客队": ev.get('awayTeam', {}).get('name', ''),
                "比分": f"{ev.get('homeScore',0)}-{ev.get('awayScore',0)}"
            })
    return {"近5次交锋": h2h}

def get_league_key(league_cn: str):
    from src.config import LEAGUE_KEY_MAP
    return LEAGUE_KEY_MAP.get(league_cn)
