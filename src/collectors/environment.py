def collect_environment(match):
    return {
        "天气": None,
        "比赛城市": None,
        "比赛场地": None,
        "场地类型": None,
        "主裁判": {"姓名": None, "场均黄牌": None, "场均点球": None, "执法风格": None, "本赛季执法场次": None},
        "未来赛程": {"主队": [], "客队": []},
        "积分排名": {"主队": None, "客队": None},
        "德比属性": None
    }
