from src.team_mapper import get_sofascore_team_id
from src.utils import fetch_json

def collect_rhythm(team_en: str):
    """上下半场进球占比"""
    team_id = get_sofascore_team_id(team_en)
    if not team_id:
        return {"上下半场占比": "", "逆转次数": None}
    url = f"https://api.sofascore.com/api/v1/team/{team_id}/statistics"
    data = fetch_json(url)
    result = {"上下半场占比": "", "逆转次数": None, "统计范围": "近10场"}
    if data and 'statistics' in data:
        for stat in data['statistics']:
            if stat.get('name') == 'Goals by half':
                result['上下半场占比'] = stat.get('value', '')
                break
    return result
