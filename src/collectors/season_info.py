def collect_season_info(match, home_en, away_en):
    return {
        "联赛": match.get("league"),
        "赛季": None,
        "当前轮次": None,
        "近5场数据构成": {"主队": None, "客队": None},
        "查询时间": None
    }
