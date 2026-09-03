from src.utils import fetch_json, now_str
from src.config import LEAGUE_MAP
from src.team_mapper import get_sofascore_team_id

def collect_season_info(match, home_en, away_en):
    """采集赛季阶段信息"""
    result = {
        "联赛": match.get('league'),
        "赛季": "2026-2027",
        "当前轮次": None,
        "主队近5场构成": {},
        "客队近5场构成": {},
        "联赛场均进球": None,
        "联赛场均失球": None,
        "来源": [],
        "获取时间": now_str()
    }
    
    league = match.get('league')
    if league and league in LEAGUE_MAP:
        tid = LEAGUE_MAP[league]['tournament_id']
        sid = LEAGUE_MAP[league]['season_id']
        standings_url = f"https://api.sofascore.com/api/v1/unique-tournament/{tid}/season/{sid}/standings/total"
        data = fetch_json(standings_url)
        if data and 'standings' in data and data['standings']:
            rows = data['standings'][0].get('rows', [])
            total_goals = 0
            total_goals_against = 0
            total_matches = 0
            for row in rows:
                total_goals += row.get('goalsScored', 0)
                total_goals_against += row.get('goalsAgainst', 0)
                total_matches += row.get('matches', 0)
            if total_matches > 0:
                result['联赛场均进球'] = round(total_goals / total_matches, 2)
                result['联赛场均失球'] = round(total_goals_against / total_matches, 2)
            result['来源'].append(standings_url)
    
    # 主队近5场
    home_id = get_sofascore_team_id(home_en)
    if home_id:
        schedule_url = f"https://api.sofascore.com/api/v1/team/{home_id}/schedule"
        data = fetch_json(schedule_url)
        if data and 'events' in data:
            recent = []
            for ev in data['events']:
                if (ev['homeTeam']['name'] == home_en and ev['awayTeam']['name'] == away_en) or \
                   (ev['homeTeam']['name'] == away_en and ev['awayTeam']['name'] == home_en):
                    continue
                if len(recent) < 5:
                    recent.append(ev)
            counts = {"本赛季联赛": 0, "上赛季联赛": 0, "国内杯赛": 0, "友谊赛": 0, "其他": 0}
            for ev in recent:
                tour = ev.get('tournament', {}).get('name', '')
                if 'Premier League' in tour or 'La Liga' in tour:
                    counts['本赛季联赛'] += 1
                elif 'Cup' in tour or 'Copa' in tour:
                    counts['国内杯赛'] += 1
                elif 'Friendly' in tour:
                    counts['友谊赛'] += 1
                else:
                    counts['其他'] += 1
            result['主队近5场构成'] = counts
            result['来源'].append(schedule_url)
    
    # 客队近5场
    away_id = get_sofascore_team_id(away_en)
    if away_id:
        schedule_url = f"https://api.sofascore.com/api/v1/team/{away_id}/schedule"
        data = fetch_json(schedule_url)
        if data and 'events' in data:
            recent = []
            for ev in data['events']:
                if (ev['homeTeam']['name'] == home_en and ev['awayTeam']['name'] == away_en) or \
                   (ev['homeTeam']['name'] == away_en and ev['awayTeam']['name'] == home_en):
                    continue
                if len(recent) < 5:
                    recent.append(ev)
            counts = {"本赛季联赛": 0, "上赛季联赛": 0, "国内杯赛": 0, "友谊赛": 0, "其他": 0}
            for ev in recent:
                tour = ev.get('tournament', {}).get('name', '')
                if 'Premier League' in tour or 'La Liga' in tour:
                    counts['本赛季联赛'] += 1
                elif 'Cup' in tour or 'Copa' in tour:
                    counts['国内杯赛'] += 1
                elif 'Friendly' in tour:
                    counts['友谊赛'] += 1
                else:
                    counts['其他'] += 1
            result['客队近5场构成'] = counts
            result['来源'].append(schedule_url)
    
    return result
