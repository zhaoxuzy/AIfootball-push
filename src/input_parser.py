import re
from datetime import datetime

def parse_match_input(text: str, target_date: str = None) -> list:
    """
    支持两种格式：
    1. 旧格式：比赛编号|联赛|主队|客队|日期（可选）
    2. 新格式：周四005 法甲 图卢兹 VS 里尔
    """
    matches = []
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # 尝试匹配新格式：如 "周四005 法甲 图卢兹 VS 里尔"
        pattern = r'^([^\s]+)\s+([^\s]+)\s+(.+?)\s+VS\s+(.+)$'
        m = re.match(pattern, line, re.IGNORECASE)
        if m:
            match_no = m.group(1).strip()
            league = m.group(2).strip()
            home = m.group(3).strip()
            away = m.group(4).strip()
            date = target_date or datetime.now().strftime("%Y-%m-%d")
            matches.append({
                'match_no': match_no,
                'league': league,
                'home_team': home,
                'away_team': away,
                'date': date
            })
            continue

        # 旧格式（管道分隔）
        parts = line.split('|')
        if len(parts) < 4:
            print(f"忽略无效行: {line}")
            continue
        match_no = parts[0].strip()
        league = parts[1].strip()
        home = parts[2].strip()
        away = parts[3].strip()
        date = parts[4].strip() if len(parts) > 4 else target_date
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        matches.append({
            'match_no': match_no,
            'league': league,
            'home_team': home,
            'away_team': away,
            'date': date
        })
    return matches
