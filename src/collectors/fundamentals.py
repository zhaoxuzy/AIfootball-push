import requests
import re
import soccerdata as sd
from soccerdata import FBref
from datetime import datetime, timedelta

# 中文联赛到 soccerdata 联赛 key 的映射（只保留 FBref 支持的联赛）
LEAGUE_KEY_MAP = {
    "英格兰超级联赛": "ENG-Premier League",
    "西班牙甲级联赛": "ESP-La Liga",
    "意大利甲级联赛": "ITA-Serie A",
    "德国甲级联赛": "GER-Bundesliga",
    "法国甲级联赛": "FRA-Ligue 1",
    "欧洲冠军联赛": "INT-World Cup",  # 欧冠可能不支持，但保留
}

def get_league_key(league_cn):
    """根据中文联赛名获取 soccerdata 使用的联赛 key，未映射或 FBref 不支持时返回 None"""
    key = LEAGUE_KEY_MAP.get(league_cn)
    if key and key in FBref.valid_leagues():
        return key
    return None

def collect_elo(team_name_en):
    """尝试从 ClubElo API 获取 Elo 评分（暂未实现具体解析）"""
    data = {"Elo评分": None, "来源": None, "来源URL": None, "更新时间": None}
    if not team_name_en:
        return data
    # ClubElo API 需要精确的球队名，此处仅占位，后续完善
    return data

def collect_xg(team_name_en, league_key, season="2026-2027"):
    """使用 FBref 获取球队 xG/xGA"""
    data = {"本赛季xG": None, "本赛季xGA": None, "近5场xG": None, "近5场xGA": None,
            "xG来源": None, "xG是否替代指标": False}
    if not team_name_en or not league_key:
        return data
    try:
        fbref = FBref(leagues=league_key, seasons=season)
        team_stats = fbref.read_team_season_stats()
        # 查找球队（可能名称不完全一致，尝试模糊匹配）
        matches = team_stats[team_stats['team'].str.contains(team_name_en, case=False, na=False)]
        if not matches.empty:
            row = matches.iloc[0]
            data["本赛季xG"] = row.get("xg")
            data["本赛季xGA"] = row.get("xga")
            data["xG来源"] = "FBref"
            # 近5场 xG 需要从比赛数据计算，此处暂不实现
        else:
            print(f"FBref 未找到球队 {team_name_en}")
    except Exception as e:
        print(f"xG获取失败: {e}")
    return data

def collect_recent_form(team_name_en, league_key, season="2026-2027"):
    """使用 FBref 获取近期战绩与攻防数据"""
    data = {
        "近5场战绩": None,
        "近5场进球": None,
        "近5场失球": None,
        "近5场对手及赛事类型": None,
        "主场场均进球": None,
        "主场场均失球": None,
        "主场战绩": None,
        "客场场均进球": None,
        "客场场均失球": None,
        "客场战绩": None,
        "胜率": None
    }
    if not team_name_en or not league_key:
        return data
    try:
        fbref = FBref(leagues=league_key, seasons=season)
        matches = fbref.read_schedule()
        # 筛选主队或客队为 team_name_en 的比赛
        team_matches = matches[(matches['home_team'] == team_name_en) | (matches['away_team'] == team_name_en)]
        if team_matches.empty:
            # 尝试模糊匹配
            team_matches = matches[(matches['home_team'].str.contains(team_name_en, case=False, na=False)) |
                                   (matches['away_team'].str.contains(team_name_en, case=False, na=False))]
        if team_matches.empty:
            print(f"FBref 未找到球队 {team_name_en}")
            return data

        team_matches = team_matches.sort_values('date', ascending=False)
        recent5 = team_matches.head(5)

        wins = draws = losses = 0
        goals_for = goals_against = 0
        opponents = []
        for _, row in recent5.iterrows():
            if row['home_team'] == team_name_en:
                gf = row['home_score']
                ga = row['away_score']
                if gf > ga:
                    wins += 1
                elif gf == ga:
                    draws += 1
                else:
                    losses += 1
                opponents.append(f"{row['away_team']} (客)")
            else:
                gf = row['away_score']
                ga = row['home_score']
                if gf > ga:
                    wins += 1
                elif gf == ga:
                    draws += 1
                else:
                    losses += 1
                opponents.append(f"{row['home_team']} (主)")
            goals_for += gf
            goals_against += ga

        data["近5场战绩"] = f"{wins}W {draws}D {losses}L"
        data["近5场进球"] = goals_for
        data["近5场失球"] = goals_against
        data["近5场对手及赛事类型"] = opponents

        # 计算主客场数据（本赛季所有比赛）
        home_matches = team_matches[team_matches['home_team'] == team_name_en]
        away_matches = team_matches[team_matches['away_team'] == team_name_en]
        if len(home_matches) > 0:
            data["主场场均进球"] = home_matches['home_score'].mean()
            data["主场场均失球"] = home_matches['away_score'].mean()
            home_wins = (home_matches['home_score'] > home_matches['away_score']).sum()
            home_draws = (home_matches['home_score'] == home_matches['away_score']).sum()
            home_losses = (home_matches['home_score'] < home_matches['away_score']).sum()
            data["主场战绩"] = f"{home_wins}W {home_draws}D {home_losses}L"
        if len(away_matches) > 0:
            data["客场场均进球"] = away_matches['away_score'].mean()
            data["客场场均失球"] = away_matches['home_score'].mean()
            away_wins = (away_matches['away_score'] > away_matches['home_score']).sum()
            away_draws = (away_matches['away_score'] == away_matches['home_score']).sum()
            away_losses = (away_matches['away_score'] < away_matches['home_score']).sum()
            data["客场战绩"] = f"{away_wins}W {away_draws}D {away_losses}L"

        total_matches = len(team_matches)
        if total_matches > 0:
            data["胜率"] = (wins + draws / 2) / total_matches
    except Exception as e:
        print(f"近期战绩获取失败: {e}")
    return data

def collect_injuries(team_name_en):
    """伤停名单暂不实现"""
    return {"伤停球员": [], "预计首发完整性": None}

def collect_coach_info(team_name_en):
    """主教练信息暂不实现"""
    return {"姓名": None, "上任时间": None, "执教风格": None}

def collect_head_to_head(home_en, away_en):
    """历史交锋暂不实现"""
    return {"近5次交锋": []}
