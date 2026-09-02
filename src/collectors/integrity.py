def self_check(match_data):
    missing_paths = []
    for key, value in match_data.items():
        if value is None or (isinstance(value, dict) and all(v is None for v in value.values())):
            missing_paths.append(key)
    risk = []
    if match_data.get("竞彩盘口", {}).get("胜平负", {}).get("即赔", {}).get("主胜") is None:
        risk.append("竞彩胜平负即赔未获取")
    return {
        "xG获取": "否",
        "Elo获取": "否",
        "伤停获取": "否",
        "竞彩赔率获取": "是" if match_data.get("竞彩盘口", {}).get("胜平负", {}).get("即赔", {}).get("主胜") else "否",
        "伤停信息完整度": "低",
        "数据适用性": "低",
        "数据覆盖等级": "低",
        "缺失项": missing_paths,
        "风险提示": risk
    }
