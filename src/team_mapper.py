"""
球队中文名 -> 英文名映射（覆盖五大联赛及主要联赛）
未映射的球队会通过SofaScore搜索自动补全并缓存。
"""
import json
from pathlib import Path
from src.utils import fetch_json

# ===== 中文->英文映射表（按联赛分组） =====
TEAM_NAME_MAP = {
    # ---- 英超 ----
    "曼城": "Manchester City",
    "阿森纳": "Arsenal",
    "利物浦": "Liverpool",
    "切尔西": "Chelsea",
    "曼联": "Manchester United",
    "热刺": "Tottenham Hotspur",
    "纽卡斯尔": "Newcastle United",
    "阿斯顿维拉": "Aston Villa",
    "布莱顿": "Brighton & Hove Albion",
    "狼队": "Wolverhampton Wanderers",
    "西汉姆联": "West Ham United",
    "水晶宫": "Crystal Palace",
    "富勒姆": "Fulham",
    "伯恩茅斯": "AFC Bournemouth",
    "诺丁汉森林": "Nottingham Forest",
    "布伦特福德": "Brentford",
    "埃弗顿": "Everton",
    "莱斯特城": "Leicester City",
    "南安普顿": "Southampton",
    "伊普斯维奇": "Ipswich Town",
    "卢顿": "Luton Town",
    "谢菲联": "Sheffield United",
    "伯恩利": "Burnley",

    # ---- 西甲 ----
    "皇家马德里": "Real Madrid",
    "巴塞罗那": "Barcelona",
    "马德里竞技": "Atletico Madrid",
    "塞维利亚": "Sevilla",
    "皇家社会": "Real Sociedad",
    "比利亚雷亚尔": "Villarreal",
    "毕尔巴鄂竞技": "Athletic Bilbao",
    "瓦伦西亚": "Valencia",
    "赫塔菲": "Getafe",
    "奥萨苏纳": "Osasuna",
    "西班牙人": "Espanyol",
    "马洛卡": "Mallorca",
    "塞尔塔": "Celta Vigo",
    "加的斯": "Cadiz",
    "格拉纳达": "Granada",
    "埃尔切": "Elche",
    "阿尔梅里亚": "Almeria",
    "巴列卡诺": "Rayo Vallecano",
    "赫罗纳": "Girona",
    "拉斯帕尔马斯": "Las Palmas",
    "莱万特": "Levante",
    "阿拉维斯": "Alaves",
    "贝蒂斯": "Real Betis",

    # ---- 意甲 ----
    "AC米兰": "AC Milan",
    "国际米兰": "Inter Milan",
    "尤文图斯": "Juventus",
    "罗马": "Roma",
    "那不勒斯": "Napoli",
    "拉齐奥": "Lazio",
    "亚特兰大": "Atalanta",
    "佛罗伦萨": "Fiorentina",
    "博洛尼亚": "Bologna",
    "都灵": "Torino",
    "乌迪内斯": "Udinese",
    "萨索洛": "Sassuolo",
    "蒙扎": "Monza",
    "热那亚": "Genoa",
    "维罗纳": "Verona",
    "莱切": "Lecce",
    "卡利亚里": "Cagliari",
    "恩波利": "Empoli",
    "萨勒尼塔纳": "Salernitana",
    "帕尔马": "Parma",
    "斯佩齐亚": "Spezia",
    "克雷莫内塞": "Cremonese",

    # ---- 德甲 ----
    "拜仁慕尼黑": "Bayern Munich",
    "多特蒙德": "Borussia Dortmund",
    "RB莱比锡": "RB Leipzig",
    "勒沃库森": "Bayer Leverkusen",
    "法兰克福": "Eintracht Frankfurt",
    "门兴": "Borussia Monchengladbach",
    "沃尔夫斯堡": "Wolfsburg",
    "柏林联合": "Union Berlin",
    "弗赖堡": "Freiburg",
    "美因茨": "Mainz 05",
    "科隆": "Cologne",
    "霍芬海姆": "Hoffenheim",
    "斯图加特": "Stuttgart",
    "奥格斯堡": "Augsburg",
    "波鸿": "Bochum",
    "云达不莱梅": "Werder Bremen",
    "达姆施塔特": "Darmstadt",
    "海登海姆": "Heidenheim",
    "基尔": "Holstein Kiel",

    # ---- 法甲 ----
    "巴黎圣日耳曼": "PSG",
    "马赛": "Marseille",
    "里昂": "Lyon",
    "摩纳哥": "Monaco",
    "里尔": "Lille",
    "尼斯": "Nice",
    "雷恩": "Rennes",
    "朗斯": "Lens",
    "斯特拉斯堡": "Strasbourg",
    "蒙彼利埃": "Montpellier",
    "图卢兹": "Toulouse",
    "南特": "Nantes",
    "兰斯": "Reims",
    "布雷斯特": "Brest",
    "克莱蒙": "Clermont",
    "洛里昂": "Lorient",
    "欧塞尔": "Auxerre",
    "阿雅克肖": "Ajaccio",
    "特鲁瓦": "Troyes",
    "圣埃蒂安": "Saint-Etienne",

    # ---- 葡超 ----
    "本菲卡": "Benfica",
    "波尔图": "Porto",
    "里斯本竞技": "Sporting CP",
    "布拉加": "Braga",
    "吉马良斯": "Vitoria Guimaraes",
    "法马利康": "Famalicao",
    "里奥阿维": "Rio Ave",
    "博阿维斯塔": "Boavista",
    "阿罗卡": "Arouca",
    "埃斯托里尔": "Estoril",

    # ---- 荷甲 ----
    "阿贾克斯": "Ajax",
    "埃因霍温": "PSV Eindhoven",
    "费耶诺德": "Feyenoord",
    "阿尔克马尔": "AZ Alkmaar",
    "特温特": "FC Twente",
    "乌德勒支": "FC Utrecht",
    "海伦芬": "Heerenveen",
    "格罗宁根": "Groningen",
    "维特斯": "Vitesse",

    # ---- 俄超 ----
    "泽尼特": "Zenit St. Petersburg",
    "莫斯科中央陆军": "CSKA Moscow",
    "莫斯科斯巴达": "Spartak Moscow",
    "莫斯科迪纳摩": "Dynamo Moscow",
    "克拉斯诺达尔": "Krasnodar",
    "罗斯托夫": "Rostov",
    "索契": "Sochi",

    # ---- 土超 ----
    "加拉塔萨雷": "Galatasaray",
    "费内巴切": "Fenerbahce",
    "贝西克塔斯": "Besiktas",
    "特拉布宗": "Trabzonspor",
    "巴萨克赛尔": "Istanbul Basaksehir",
    "阿兰亚斯堡": "Alanyaspor",

    # ---- 比甲 ----
    "布鲁日": "Club Brugge",
    "安德莱赫特": "Anderlecht",
    "根特": "Gent",
    "标准列日": "Standard Liege",
    "亨克": "Genk",
    "梅赫伦": "Mechelen",

    # ---- 苏超 ----
    "凯尔特人": "Celtic",
    "流浪者": "Rangers",
    "阿伯丁": "Aberdeen",
    "哈茨": "Hearts",
    "希伯尼安": "Hibernian",

    # ---- 奥超 ----
    "萨尔茨堡红牛": "Red Bull Salzburg",
    "维也纳快速": "Rapid Vienna",
    "奥地利维也纳": "Austria Vienna",
    "格拉茨风暴": "Sturm Graz",

    # ---- 丹超 ----
    "哥本哈根": "FC Copenhagen",
    "中日德兰": "Midtjylland",
    "布隆德比": "Brondby",
    "奥尔堡": "Aalborg",
    "奥胡斯": "Aarhus",

    # ---- 瑞典超 ----
    "马尔默": "Malmo FF",
    "AIK索尔纳": "AIK Stockholm",
    "佐加顿斯": "Djurgardens",
    "哈马比": "Hammarby",
    "埃尔夫斯堡": "Elfsborg",
    "北雪平": "Norrkoping",
    "赫根": "Hacken",
    "卡尔马": "Kalmar",

    # ---- 挪超 ----
    "博德闪耀": "Bodo/Glimt",
    "莫尔德": "Molde",
    "罗森博格": "Rosenborg",
    "瓦勒伦加": "Valerenga",
    "斯塔贝克": "Stabaek",
    "维京": "Viking",
    "奥勒松": "Aalesund",

    # ---- 芬超 ----
    "赫尔辛基": "HJK Helsinki",
    "库奥皮奥": "KuPS",
    "塞伊奈约基": "SJK",
    "哈卡": "Haka",
    "拉赫蒂": "Lahti",

    # ---- 韩职 ----
    "全北现代": "Jeonbuk Motors",
    "蔚山现代": "Ulsan Hyundai",
    "首尔FC": "FC Seoul",
    "大邱FC": "Daegu FC",
    "水原三星": "Suwon Samsung",
    "济州联": "Jeju United",
    "浦项制铁": "Pohang Steelers",
    "仁川联": "Incheon United",
    "江原FC": "Gangwon FC",
    "光州FC": "Gwangju FC",
    "城南FC": "Seongnam FC",

    # ---- 沙职 ----
    "利雅得新月": "Al Hilal",
    "利雅得胜利": "Al Nassr",
    "吉达联合": "Al Ittihad",
    "吉达国民": "Al Ahli",
    "利雅得青年": "Al Shabab",
    "达曼协作": "Al Ettifaq",
    "布赖代合作": "Al Taawoun",

    # ---- 日职 ----
    "川崎前锋": "Kawasaki Frontale",
    "横滨水手": "Yokohama F Marinos",
    "神户胜利船": "Vissel Kobe",
    "浦和红钻": "Urawa Red Diamonds",
    "名古屋鲸八": "Nagoya Grampus",
    "鹿岛鹿角": "Kashima Antlers",
    "大阪樱花": "Cerezo Osaka",
    "大阪钢巴": "Gamba Osaka",
    "东京FC": "FC Tokyo",
    "广岛三箭": "Sanfrecce Hiroshima",
    "柏太阳神": "Kashiwa Reysol",
    "札幌冈萨多": "Consadole Sapporo",

    # ---- 美职联 ----
    "洛杉矶FC": "LAFC",
    "洛杉矶银河": "LA Galaxy",
    "迈阿密国际": "Inter Miami",
    "纽约红牛": "New York Red Bulls",
    "纽约城": "New York City FC",
    "亚特兰大联": "Atlanta United",
    "西雅图海湾人": "Seattle Sounders",
    "波特兰伐木工": "Portland Timbers",
    "堪萨斯城竞技": "Sporting Kansas City",

    # ---- 其他欧洲 ----
    "巴塞尔": "Basel",
    "年轻人": "Young Boys",
    "费伦茨瓦罗斯": "Ferencvaros",
    "贝尔格莱德红星": "Red Star Belgrade",
    "萨格勒布迪纳摩": "Dinamo Zagreb",
    "布拉格斯拉维亚": "Slavia Prague",
    "布拉格斯巴达": "Sparta Prague",
}

# SofaScore 球队ID缓存
SOFASCORE_TEAM_ID_CACHE = {}
CACHE_FILE = Path(__file__).parent.parent / "team_cache.json"

def load_cache():
    global SOFASCORE_TEAM_ID_CACHE
    if CACHE_FILE.exists():
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            SOFASCORE_TEAM_ID_CACHE = json.load(f)

def save_cache():
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(SOFASCORE_TEAM_ID_CACHE, f, ensure_ascii=False, indent=2)

def get_english_team_name(chinese_name: str) -> str:
    """返回英文名，若未在映射表中，则尝试通过SofaScore搜索获取并缓存"""
    if chinese_name in TEAM_NAME_MAP:
        return TEAM_NAME_MAP[chinese_name]
    print(f"未找到映射，尝试搜索: {chinese_name}")
    en_name = search_team_name(chinese_name)
    if en_name:
        TEAM_NAME_MAP[chinese_name] = en_name
        return en_name
    return chinese_name

def search_team_name(chinese_name: str) -> str:
    """通过SofaScore搜索API查找英文名"""
    url = f"https://api.sofascore.com/api/v1/search?q={chinese_name}"
    data = fetch_json(url)
    if data and 'results' in data:
        for item in data['results']:
            if item['type'] == 'team':
                return item['name']
    return None

def get_sofascore_team_id(team_en: str) -> int:
    """根据英文名获取SofaScore球队ID（带缓存）"""
    load_cache()
    if team_en in SOFASCORE_TEAM_ID_CACHE:
        return SOFASCORE_TEAM_ID_CACHE[team_en]
    url = f"https://api.sofascore.com/api/v1/search?q={team_en.replace(' ', '%20')}"
    data = fetch_json(url)
    if data and 'results' in data:
        for item in data['results']:
            if item['type'] == 'team' and item['name'].lower() == team_en.lower():
                team_id = item['id']
                SOFASCORE_TEAM_ID_CACHE[team_en] = team_id
                save_cache()
                return team_id
    return None
