import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# 주제별 키워드 (순서 = 사이트 주제 칩 표시 순서). 행사명 기준 매칭.
# - 한글 키워드: 부분 문자열 매칭
# - 영문 키워드: 단어 단위 매칭 (Fair 안의 "ai", Every 안의 "ev" 같은 오탐 방지)
TOPICS: dict[str, list[str]] = {
    "리테일/유통": [
        "리테일", "retail", "유통", "커머스", "commerce", "프랜차이즈", "franchise",
        "창업", "소상공인", "자영업", "백화점", "쇼핑", "shopping", "마켓", "market",
        "프리마켓", "플리마켓", "브랜드", "brand", "무역", "수출", "소싱", "sourcing",
        "선물", "gift", "판촉", "프로모션", "물류", "logistics", "콜드체인",
        "포장", "패키징", "packaging", "편의점", "도소매", "상품", "굿즈",
        "쇼룸", "showroom", "팝업", "popup", "pop-up", "상점", "스토어", "store", "바자",
    ],
    "식품/F&B": [
        "식품", "푸드", "food", "f&b", "음식", "외식", "레스토랑", "다이닝", "미식",
        "커피", "coffee", "카페", "cafe", "베이커리", "bakery", "디저트", "dessert",
        "와인", "wine", "주류", "맥주", "beer", "위스키", "whisky", "캐스크", "cask",
        "티&", "티 &", "tea", "차문화", "식자재", "농식품", "농수산", "수산물", "축산물",
        "건강기능식품", "비건", "vegan", "요리", "쿠킹", "cooking", "바리스타",
    ],
    "패션/뷰티": [
        "패션", "fashion", "의류", "어패럴", "apparel", "텍스타일", "textile", "섬유",
        "텍스", "tex", "신발", "슈즈", "shoes", "가방", "bag", "한복", "hermès", "hermes", "주얼리", "jewelry",
        "시계", "watch", "액세서리", "안경", "아이웨어", "eyewear",
        "뷰티", "beauty", "화장품", "코스메틱", "cosmetic", "네일", "nail", "헤어", "hair",
        "미용", "피부", "스킨", "skin", "향수", "퍼퓸", "메이크업",
    ],
    "리빙/건축/인테리어": [
        "리빙", "living", "홈", "home", "인테리어", "interior", "건축", "architecture",
        "건설", "가구", "furniture", "조명", "lighting", "주방", "키친", "kitchen",
        "욕실", "타일", "침구", "데코", "deco", "홈데코", "조경", "정원", "가든", "garden",
        "부동산", "주택", "하우징", "housing", "집코노미", "공간", "space", "스마트홈",
    ],
    "AI/IT/로보틱스": [
        "ai", "aiot", "인공지능", "머신러닝", "딥러닝", "데이터", "data",
        "로봇", "robot", "로보틱스", "robotics", "자동화", "automation",
        "it", "소프트웨어", "software", "디지털", "digital", "테크", "tech",
        "클라우드", "cloud", "iot", "반도체", "semiconductor", "전자", "electronics",
        "스마트", "smart", "메타버스", "metaverse", "블록체인", "blockchain",
        "보안", "security", "드론", "drone", "자율주행", "모빌리티", "mobility",
        "배터리", "battery", "ev", "xev", "dx", "saas", "5g", "6g",
        "퀀텀", "quantum", "스타트업", "startup",
    ],
    "디자인/문화/예술": [
        "디자인", "design", "아트", "art", "미술", "작가", "갤러리", "gallery",
        "공예", "크래프트", "craft", "사진", "포토", "photo", "일러스트", "그래픽",
        "컬처", "culture", "문화", "예술", "콘서트", "concert", "공연", "뮤지컬",
        "음악", "뮤직", "music", "영화", "film", "북", "도서", "출판", "책",
        "캐릭터", "만화", "웹툰", "애니", "조형", "라이트", "light", "빛", "컬러", "color",
        "색", "헤리티지", "heritage", "전통", "한국의",
        "기획전", "특별전", "교류전", "협력전시", "기념전", "역사관", "기념관",
        "라이브러리", "library", "매거진", "magazine", "버스킹", "busking", "댄스", "dance",
        "스테이지", "stage", "드럼", "밴드", "band", "bts", "k-pop", "케이팝", "아이돌", "팬",
        "메이커", "maker", "핸드메이드", "handmade",
    ],
    "키즈/베이비/교육": [
        "키즈", "kids", "베이비", "baby", "유아", "아동", "어린이", "임신", "출산",
        "맘", "mom", "육아", "교육", "education", "에듀", "edu", "학습", "유학",
        "입시", "진로", "장난감", "토이", "toy", "완구", "학원", "스쿨", "school",
        "아기", "대학", "입학",
    ],
    "라이프스타일/레저": [
        "라이프스타일", "lifestyle", "레저", "leisure", "캠핑", "camping",
        "아웃도어", "outdoor", "여행", "관광", "트래블", "travel", "스포츠", "sports",
        "러닝", "running", "마라톤", "골프", "golf", "피트니스", "fitness", "헬스", "요가",
        "반려", "펫", "pet", "고양이", "캣", "cat", "강아지", "dog", "취미", "하비", "hobby",
        "게임", "game", "보드게임", "낚시", "자전거", "바이크", "bike", "오토", "auto",
        "자동차", "모터", "motor", "웰니스", "wellness", "건강", "시니어", "웨딩", "wedding",
        "브라이덜", "주짓수", "챔피언", "축제", "문구", "레포츠",
    ],
}

# 어느 주제에도 매칭되지 않으면 부여되는 주제. 사이트의 "관련 주제만" 스위치는 이것을 제외한다.
OTHER_TOPIC = "기타"
ALL_TOPICS = [*TOPICS, OTHER_TOPIC]

# 주제별 제외어: 해당 주제 매칭 전에 행사명에서 지운다 (다른 주제 매칭에는 영향 없음)
TOPIC_EXCLUDES: dict[str, list[str]] = {
    "AI/IT/로보틱스": ["재테크", "푸드테크", "에듀테크", "뷰티테크", "패션테크"],
    "리테일/유통": ["재테크"],
}

_ASCII = re.compile(r"^[\x00-\x7f]+$")


def _compile(keyword: str) -> re.Pattern:
    k = keyword.lower()
    if _ASCII.match(k):
        return re.compile(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])")
    return re.compile(re.escape(k))


_TOPIC_PATTERNS = {
    topic: [_compile(k) for k in keywords] for topic, keywords in TOPICS.items()
}

# 하위 호환: 전체 키워드 평면 리스트
KEYWORDS = [k for keywords in TOPICS.values() for k in keywords]


def topics_of(event: dict) -> List[str]:
    """행사명에 매칭되는 주제 목록 (TOPICS 순서). 하나도 없으면 [OTHER_TOPIC]."""
    name = event.get("name", "").lower()
    matched = []
    for topic, patterns in _TOPIC_PATTERNS.items():
        text = name
        for ex in TOPIC_EXCLUDES.get(topic, []):
            text = text.replace(ex.lower(), " ")
        if any(p.search(text) for p in patterns):
            matched.append(topic)
    return matched or [OTHER_TOPIC]


def is_relevant(event: dict) -> bool:
    """개별 이벤트의 관련 여부 = '기타' 외의 주제가 하나 이상 매칭되는지."""
    return topics_of(event) != [OTHER_TOPIC]


def filter_relevant(events: List[dict]) -> List[dict]:
    """'기타'가 아닌 주제에 해당하는 행사만 필터링한다."""
    result = [e for e in events if is_relevant(e)]
    logger.info("전체 %d개 중 %d개 선별", len(events), len(result))
    return result
