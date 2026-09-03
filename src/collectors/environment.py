from src.utils import fetch_json, now_str
from src.config import OPENWEATHER_API_KEY

def collect_environment(match):
    """天气、主裁判、主教练、排名等"""
    weather = {}
    if OPENWEATHER_API_KEY:
        city = match.get('home_team', '')
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=zh_cn"
        data = fetch_json(url)
        if data and 'weather' in data:
            weather = {"天气": data['weather'][0]['description'], "温度": data['main']['temp']}
    return {
        "天气": weather,
        "主裁判": {"姓名": None, "场均黄牌": None, "场均点球": None, "执法风格": None},
        "主教练": {},
        "未来赛程": {"主队": [], "客队": []},
        "积分排名": {},
        "德比属性": "无",
        "场地": None,
        "来源": "手动/API",
        "获取时间": now_str()
    }
