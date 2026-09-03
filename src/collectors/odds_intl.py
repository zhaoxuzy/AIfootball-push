from src.utils import fetch_json, now_str
from src.team_mapper import get_sofascore_team_id

def collect_international_odds(match):
    """国际赔率：从SofaScore赔率API获取"""
    home_en = match.get('home_team_en')
    away_en = match.get('away_team_en')
    if not home_en or not away_en:
        return {"亚盘": {}, "大小球": {}, "欧赔": []}
    
    # 搜索比赛ID
    search_url = f"https://api.sofascore.com/api/v1/search?q={home_en.replace(' ', '%20')}%20{away_en.replace(' ', '%20')}"
    data = fetch_json(search_url)
    match_id = None
    if data and 'results' in data:
        for ev in data['results']:
            if ev['type'] == 'event':
                match_id = ev['id']
                break
    if not match_id:
        return {"亚盘": {}, "大小球": {}, "欧赔": []}
    
    odds_url = f"https://api.sofascore.com/api/v1/event/{match_id}/odds"
    odds_data = fetch_json(odds_url)
    result = {
        "亚盘": {"初盘": {}, "即盘": {}},
        "大小球": {"初盘": {}, "即盘": {}},
        "欧赔": [],
        "来源": odds_url,
        "获取时间": now_str()
    }
    if odds_data and 'markets' in odds_data:
        for market in odds_data['markets']:
            if market.get('name') == 'Asian handicap':
                choices = market.get('choices', [])
                if choices:
                    result['亚盘']['初盘'] = {
                        "让球数": choices[0].get('handicap', 0),
                        "水位": choices[0].get('price', 0)
                    }
            if market.get('name') == 'Over/Under':
                choices = market.get('choices', [])
                if choices:
                    result['大小球']['初盘'] = {
                        "盘口": choices[0].get('handicap', 2.5),
                        "大球水位": choices[0].get('price', 0),
                        "小球水位": choices[1].get('price', 0) if len(choices) > 1 else None
                    }
            if market.get('name') == '1X2':
                for choice in market.get('choices', []):
                    result['欧赔'].append({
                        "机构": market.get('bookmaker', 'unknown'),
                        "主胜": choice.get('price', 0) if choice.get('name') == 'Home' else None,
                        "平": choice.get('price', 0) if choice.get('name') == 'Draw' else None,
                        "客胜": choice.get('price', 0) if choice.get('name') == 'Away' else None
                    })
    return result
