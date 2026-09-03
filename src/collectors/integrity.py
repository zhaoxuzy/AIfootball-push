def self_check(match_data):
    """根据采集结果评定数据完整度和覆盖等级"""
    missing = []
    
    if not match_data.get('竞彩盘口', {}).get('胜平负', {}).get('即赔', {}).get('主胜'):
        missing.append('竞彩胜平负即赔缺失')
    if not match_data.get('国际赔率', {}).get('大小球', {}).get('初盘'):
        missing.append('大小球盘口缺失')
    if not match_data.get('基本面', {}).get('主队', {}).get('xG', {}).get('赛季xG'):
        missing.append('主队xG缺失')
    if not match_data.get('基本面', {}).get('客队', {}).get('xG', {}).get('赛季xG'):
        missing.append('客队xG缺失')
    if not match_data.get('节奏数据', {}).get('主队', {}).get('上下半场占比'):
        missing.append('主队上下半场占比缺失')
    if not match_data.get('节奏数据', {}).get('客队', {}).get('上下半场占比'):
        missing.append('客队上下半场占比缺失')
    
    injury_level = '低'
    has_odds = bool(match_data.get('竞彩盘口', {}).get('胜平负', {}).get('即赔', {}).get('主胜'))
    has_size = bool(match_data.get('国际赔率', {}).get('大小球', {}).get('初盘'))
    has_xg = bool(match_data.get('基本面', {}).get('主队', {}).get('xG', {}).get('赛季xG'))
    has_half = bool(match_data.get('节奏数据', {}).get('主队', {}).get('上下半场占比'))
    
    if has_odds and has_size and has_xg and has_half:
        cover = '高'
    elif has_odds and has_size:
        cover = '中'
    elif has_odds:
        cover = '低'
    else:
        cover = 'D级'
    
    return {
        "缺失项": missing,
        "伤停信息完整度": injury_level,
        "数据适用性": "中",
        "数据覆盖等级": cover
    }
