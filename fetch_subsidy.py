#!/usr/bin/env python3
"""
여주소식 정부 지원금/보조금 자동화 스크립트
보조금24 API - 정부/지자체 공공서비스 정보
"""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import json

# ============ 설정 ============
API_KEY = os.environ.get('SUBSIDY_API_KEY', '')
WP_URL = os.environ.get('WP_URL', 'https://yeojugoodnews.com')
WP_USER = os.environ.get('WP_USER', '')
WP_APP_PASSWORD = os.environ.get('WP_APP_PASSWORD', '')

BASE_URL = 'https://api.odcloud.kr/api/gov24/v3'

# 카테고리 매핑
CATEGORIES = {
    '노인': ['노인', '어르신', '경로', '기초연금', '장기요양', '돌봄'],
    '청년': ['청년', '청소년', '대학생', '취업', '일자리', '창업'],
    '출산/육아': ['임산부', '출산', '육아', '양육', '아동', '영유아', '어린이'],
    '장애인': ['장애인', '장애', '활동지원'],
    '저소득': ['기초생활', '차상위', '긴급복지', '저소득'],
    '소상공인': ['소상공인', '자영업', '소기업', '창업지원'],
    '주거': ['주거', '월세', '전세', '임대', '주택'],
    '교육': ['교육', '장학', '학자금', '학비'],
    '기타': []
}

# 여주시/경기도 필터링 키워드
LOCAL_KEYWORDS = ['여주', '경기도', '전국']


def fetch_service_list(page: int = 1, per_page: int = 100) -> Dict:
    """공공서비스 목록 조회"""
    if not API_KEY:
        print("API 키 없음")
        return {}
    
    url = f"{BASE_URL}/serviceList"
    params = {
        'page': page,
        'perPage': per_page,
        'serviceKey': API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"API Error: {e}")
        return {}


def fetch_recent_services(days: int = 7) -> List[Dict]:
    """최근 등록/수정된 서비스 조회"""
    all_services = []
    page = 1
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    while True:
        result = fetch_service_list(page=page, per_page=100)
        if not result or 'data' not in result:
            break
        
        services = result.get('data', [])
        if not services:
            break
        
        for svc in services:
            # 최근 등록/수정된 것만 필터링
            mod_date = svc.get('수정일시', '')[:10]
            reg_date = svc.get('등록일시', '')[:10]
            
            if mod_date >= cutoff_date or reg_date >= cutoff_date:
                all_services.append(svc)
        
        # 더 이상 최근 데이터가 없으면 종료
        if len(services) < 100:
            break
        
        page += 1
        if page > 10:  # 최대 10페이지
            break
    
    return all_services


def filter_local_services(services: List[Dict]) -> List[Dict]:
    """여주시/경기도/전국 서비스 필터링"""
    filtered = []
    
    for svc in services:
        org_name = svc.get('소관기관명', '')
        support_target = svc.get('지원대상', '')
        service_name = svc.get('서비스명', '')
        
        # 여주시, 경기도, 또는 전국 단위 서비스
        is_local = False
        
        if '여주' in org_name or '여주' in service_name:
            is_local = True
        elif '경기도' in org_name:
            is_local = True
        elif svc.get('소관기관유형', '') in ['중앙행정기관', '공공기관']:
            is_local = True  # 전국 단위
        
        if is_local:
            filtered.append(svc)
    
    return filtered


def categorize_service(service: Dict) -> str:
    """서비스 카테고리 분류"""
    name = service.get('서비스명', '')
    target = service.get('지원대상', '')
    content = service.get('지원내용', '')
    text = f"{name} {target} {content}"
    
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword in text:
                return category
    
    return '기타'


def format_price(amount: str) -> str:
    """금액 포맷팅"""
    try:
        num = int(amount.replace(',', '').replace('원', '').strip())
        if num >= 10000:
            만 = num // 10000
            return f"{만}만원"
        return f"{num:,}원"
    except:
        return amount


def generate_html(services: List[Dict]) -> str:
    """HTML 콘텐츠 생성"""
    now = datetime.now()
    update_time = now.strftime('%Y-%m-%d %H:%M')
    
    # 카테고리별 분류
    categorized = {}
    for svc in services:
        cat = categorize_service(svc)
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(svc)
    
    # 카테고리 순서
    category_order = ['청년', '노인', '출산/육아', '장애인', '저소득', '소상공인', '주거', '교육', '기타']
    category_icons = {
        '청년': '👨‍🎓',
        '노인': '👴',
        '출산/육아': '👶',
        '장애인': '♿',
        '저소득': '🏠',
        '소상공인': '🏪',
        '주거': '🏡',
        '교육': '📚',
        '기타': '📋'
    }
    category_colors = {
        '청년': '#60a5fa',
        '노인': '#c084fc',
        '출산/육아': '#f472b6',
        '장애인': '#4ade80',
        '저소득': '#fbbf24',
        '소상공인': '#fb923c',
        '주거': '#2dd4bf',
        '교육': '#a78bfa',
        '기타': '#94a3b8'
    }
    
    html = f'''
<div class="yjsub">
<style>
.yjsub {{
    font-family: -apple-system, BlinkMacSystemFont, 'Malgun Gothic', sans-serif !important;
    background: #111 !important;
    color: #ddd !important;
    padding: 16px !important;
    border-radius: 12px !important;
    line-height: 1.5 !important;
}}
.yjsub * {{ box-sizing: border-box !important; margin: 0 !important; padding: 0 !important; }}
.yjsub-head {{
    background: linear-gradient(135deg, #1e40af, #0f172a) !important;
    padding: 20px !important;
    border-radius: 10px !important;
    margin-bottom: 16px !important;
    text-align: center !important;
}}
.yjsub-head h2 {{
    font-size: 20px !important;
    color: #fff !important;
    margin-bottom: 6px !important;
    border: none !important;
}}
.yjsub-head p {{
    font-size: 12px !important;
    color: rgba(255,255,255,0.6) !important;
}}
.yjsub-stats {{
    display: flex !important;
    justify-content: center !important;
    gap: 24px !important;
    margin-top: 16px !important;
}}
.yjsub-stat {{
    text-align: center !important;
}}
.yjsub-stat .lbl {{
    font-size: 11px !important;
    color: rgba(255,255,255,0.5) !important;
}}
.yjsub-stat .num {{
    font-size: 24px !important;
    font-weight: 700 !important;
    color: #60a5fa !important;
}}
.yjsub-cat {{
    margin-bottom: 20px !important;
}}
.yjsub-cat-title {{
    font-size: 15px !important;
    font-weight: 600 !important;
    color: #fff !important;
    padding: 10px 0 !important;
    border-bottom: 1px solid #333 !important;
    margin-bottom: 10px !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
}}
.yjsub-cat-title .cnt {{
    font-size: 12px !important;
    color: #888 !important;
    font-weight: 400 !important;
}}
.yjsub-list {{
    display: flex !important;
    flex-direction: column !important;
    gap: 8px !important;
}}
.yjsub-card {{
    background: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 10px !important;
    padding: 14px !important;
    cursor: pointer !important;
    transition: border-color 0.2s !important;
}}
.yjsub-card:hover {{
    border-color: #444 !important;
}}
.yjsub-card-top {{
    display: flex !important;
    justify-content: space-between !important;
    align-items: flex-start !important;
    gap: 10px !important;
    margin-bottom: 8px !important;
}}
.yjsub-card-name {{
    font-size: 14px !important;
    font-weight: 600 !important;
    color: #fff !important;
    flex: 1 !important;
}}
.yjsub-card-org {{
    font-size: 11px !important;
    color: #888 !important;
    background: #252525 !important;
    padding: 2px 8px !important;
    border-radius: 4px !important;
    flex-shrink: 0 !important;
}}
.yjsub-card-desc {{
    font-size: 12px !important;
    color: #999 !important;
    margin-bottom: 10px !important;
    display: -webkit-box !important;
    -webkit-line-clamp: 2 !important;
    -webkit-box-orient: vertical !important;
    overflow: hidden !important;
}}
.yjsub-card-meta {{
    display: flex !important;
    gap: 12px !important;
    font-size: 11px !important;
    color: #666 !important;
}}
.yjsub-card-link {{
    display: inline-block !important;
    margin-top: 10px !important;
    font-size: 12px !important;
    color: #60a5fa !important;
    text-decoration: none !important;
}}
.yjsub-footer {{
    text-align: center !important;
    padding: 16px 0 0 0 !important;
    font-size: 11px !important;
    color: #555 !important;
}}
.yjsub-footer a {{
    color: #60a5fa !important;
    text-decoration: none !important;
}}
.yjsub-empty {{
    text-align: center !important;
    padding: 30px !important;
    color: #666 !important;
}}
</style>

<div class="yjsub-head">
    <h2>📢 정부 지원금 · 보조금 안내</h2>
    <p>여주시민이 받을 수 있는 정부/지자체 지원 혜택</p>
    <div class="yjsub-stats">
        <div class="yjsub-stat">
            <div class="lbl">총 지원사업</div>
            <div class="num">{len(services)}건</div>
        </div>
    </div>
</div>
'''
    
    for cat in category_order:
        if cat not in categorized or not categorized[cat]:
            continue
        
        cat_services = categorized[cat][:10]  # 카테고리당 최대 10개
        icon = category_icons.get(cat, '📋')
        color = category_colors.get(cat, '#888')
        
        html += f'''
<div class="yjsub-cat">
    <div class="yjsub-cat-title">
        <span>{icon}</span>
        <span style="color:{color} !important;">{cat}</span>
        <span class="cnt">({len(categorized[cat])}건)</span>
    </div>
    <div class="yjsub-list">
'''
        
        for svc in cat_services:
            name = svc.get('서비스명', '')
            org = svc.get('소관기관명', '')
            desc = svc.get('서비스목적요약', '') or svc.get('지원내용', '')[:100]
            target = svc.get('지원대상', '')[:50]
            method = svc.get('신청방법', '')[:30]
            url = svc.get('상세조회URL', '')
            
            html += f'''
        <div class="yjsub-card">
            <div class="yjsub-card-top">
                <div class="yjsub-card-name">{name}</div>
                <div class="yjsub-card-org">{org}</div>
            </div>
            <div class="yjsub-card-desc">{desc}</div>
            <div class="yjsub-card-meta">
                <span>👤 {target}</span>
            </div>
            {f'<a class="yjsub-card-link" href="{url}" target="_blank">자세히 보기 →</a>' if url else ''}
        </div>
'''
        
        html += '''
    </div>
</div>
'''
    
    html += f'''
<div class="yjsub-footer">
    자료: <a href="https://www.gov.kr/portal/rcvfvrSvc/main" target="_blank">정부24 보조금24</a><br>
    업데이트: {update_time}
</div>
</div>
'''
    
    return html


def post_to_wordpress(title: str, content: str, category_id: int = None) -> bool:
    """워드프레스에 발행"""
    if not all([WP_URL, WP_USER, WP_APP_PASSWORD]):
        with open("subsidy_output.html", 'w', encoding='utf-8') as f:
            f.write(f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{title}</title></head><body style='background:#000;padding:20px;'>{content}</body></html>")
        print(f"✅ HTML 저장: subsidy_output.html")
        return False
    
    post_data = {
        'title': title,
        'content': content,
        'status': 'publish'
    }
    
    if category_id:
        post_data['categories'] = [category_id]
    
    try:
        response = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts",
            json=post_data,
            auth=(WP_USER, WP_APP_PASSWORD),
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        print(f"✅ 발행: {result.get('link', '')}")
        return True
    except Exception as e:
        print(f"발행 실패: {e}")
        return False


def main():
    print("📢 정부 지원금/보조금 정보 업데이트 시작...")
    
    # 최근 30일 내 등록/수정된 서비스 조회
    print("  서비스 목록 조회 중...")
    services = fetch_recent_services(days=30)
    print(f"  최근 업데이트: {len(services)}건")
    
    # 여주시/경기도/전국 필터링
    local_services = filter_local_services(services)
    print(f"  여주시민 대상: {len(local_services)}건")
    
    if not local_services:
        print("해당 서비스 없음")
        return
    
    # HTML 생성
    content = generate_html(local_services)
    
    # 제목 생성
    now = datetime.now()
    title = f"{now.month}월 정부 지원금·보조금 안내 ({len(local_services)}건)"
    
    # 워드프레스 발행
    post_to_wordpress(title, content, category_id=139)
    
    print("✅ 완료!")


if __name__ == '__main__':
    main()
