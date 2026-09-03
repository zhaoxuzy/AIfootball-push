import os
from datetime import timezone, timedelta

TZ = timezone(timedelta(hours=8))

# 钉钉配置
DINGTALK_WEBHOOK = os.getenv("DINGTALK_WEBHOOK", "")
DINGTALK_SECRET = os.getenv("DINGTALK_SECRET", "")

# GitHub Actions 信息
GITHUB_RUN_ID = os.getenv("GITHUB_RUN_ID", "")
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY", "")
ARTIFACT_BASE_URL = f"https://github.com/{GITHUB_REPO}/actions/runs/{GITHUB_RUN_ID}" if GITHUB_REPO else ""

# 天气API
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# 联赛映射（中文名 -> SofaScore tournament_id, season_id）
LEAGUE_MAP = {
    "英超": {"tournament_id": 17, "season_id": 52910},
    "西甲": {"tournament_id": 8, "season_id": 52912},
    "意甲": {"tournament_id": 23, "season_id": 52913},
    "德甲": {"tournament_id": 35, "season_id": 52914},
    "法甲": {"tournament_id": 34, "season_id": 52915},
    "葡超": {"tournament_id": 38, "season_id": 52916},
    "荷甲": {"tournament_id": 37, "season_id": 52917},
    "比甲": {"tournament_id": 40, "season_id": 52918},
    "苏超": {"tournament_id": 44, "season_id": 52919},
    "俄超": {"tournament_id": 42, "season_id": 52920},
    "土超": {"tournament_id": 41, "season_id": 52921},
    "丹超": {"tournament_id": 52, "season_id": 52922},
    "瑞典超": {"tournament_id": 47, "season_id": 52923},
    "挪超": {"tournament_id": 46, "season_id": 52924},
    "芬超": {"tournament_id": 50, "season_id": 52925},
    "奥超": {"tournament_id": 48, "season_id": 52926},
    "韩职": {"tournament_id": 63, "season_id": 52927},
    "沙职": {"tournament_id": 69, "season_id": 52928},
    "日职": {"tournament_id": 62, "season_id": 52929},
    "美职联": {"tournament_id": 60, "season_id": 52930},
}

# 联赛英文关键字（用于fbref）
LEAGUE_KEY_MAP = {
    "英超": "9",
    "西甲": "12",
    "意甲": "11",
    "德甲": "20",
    "法甲": "13",
    "葡超": "32",
    "荷甲": "23",
    "比甲": "36",
    "苏超": "24",
    "俄超": "31",
    "土超": "26",
    "丹超": "28",
    "瑞典超": "29",
    "挪超": "30",
    "芬超": "33",
    "奥超": "27",
    "韩职": "104",
    "沙职": "101",
    "日职": "98",
    "美职联": "22",
}
