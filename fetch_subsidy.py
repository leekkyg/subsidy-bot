#!/usr/bin/env python3
"""
여주소식 정부 지원금/보조금 자동화 스크립트
보조금24 API - 탭 UI + 드롭다운 + 섬네일
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

# 카테고리 설정
CATEGORIES = {
    'youth': {
        'name': '청년',
        'icon': '👨‍🎓',
        'color': '#60a5fa',
        'bg': '#1e3a5f',
        'keywords': ['청년', '청소년', '대학생', '취업', '일자리', '창업', '20대', '30대']
    },
    'senior': {
        'name': '노인',
        'icon': '👴',
        'color': '#c084fc',
        'bg': '#4a1d6a',
        'keywords': ['노인', '어르신', '경로', '기초연금', '장기요양', '돌봄', '65세', '고령']
    },
    'family': {
        'name': '출산/육아',
        'icon': '👶',
        'color': '#f472b6',
        'bg': '#831843',
        'keywords': ['임산부', '출산', '육아', '양육', '아동', '영유아', '어린이', '임신', '신생아']
    },
    'disabled': {
        'name': '장애인',
        'icon': '♿',
        'color': '#4ade80',
        'bg': '#14532d',
        'keywords': ['장애인', '장애', '활동지원', '보조기기']
    },
    'lowincome': {
        'name': '저소득',
        'icon': '🏠',
        'color': '#fbbf24',
        'bg': '#713f12',
        'keywords': ['기초생활', '차상위', '긴급복지', '저소득', '기초수급', '생계급여']
    },
    'business': {
        'name': '소상공인',
        'icon': '🏪',
        'color': '#fb923c',
        'bg': '#7c2d12',
        'keywords': ['소상공인', '자영업', '소기업', '창업지원', '사업자']
    },
    'etc': {
        'name': '기타',
        'icon': '📋',
        'color': '#94a3b8',
        'bg': '#334155',
        'keywords': []
    }
}

CATEGORY_ORDER = ['youth', 'senior', 'family', 'disabled', 'lowincome', 'business', 'etc']


def fetch_service_list(page: int = 1, per_page: int = 100) -> Dict:
    """공공서비스 목록 조회"""
    if not API_KEY:
        print("  API 키 없음")
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
        print(f"  API Error: {e}")
        return {}


def fetch_all_services(max_pages: int = 20) -> List[Dict]:
    """전체 서비스 목록 조회"""
    all_services = []
    
    for page in range(1, max_pages + 1):
        result = fetch_service_list(page=page, per_page=100)
        if not result or 'data' not in result:
            break
        
        services = result.get('data', [])
        if not services:
            break
        
        all_services.extend(services)
        
        total = result.get('totalCount', 0)
        if len(all_services) >= total:
            break
    
    return all_services


def filter_local_services(services: List[Dict]) -> List[Dict]:
    """여주시/경기도/전국 서비스 필터링"""
    filtered = []
    
    for svc in services:
        org_name = svc.get('소관기관명', '')
        org_type = svc.get('소관기관유형', '')
        
        is_local = False
        
        if '여주' in org_name:
            is_local = True
        elif '경기도' in org_name:
            is_local = True
        elif org_type in ['중앙행정기관', '공공기관']:
            is_local = True
        
        if is_local:
            filtered.append(svc)
    
    return filtered


def categorize_service(service: Dict) -> str:
    """서비스 카테고리 분류"""
    name = service.get('서비스명', '')
    target = service.get('지원대상', '')
    content = service.get('지원내용', '')
    text = f"{name} {target} {content}"
    
    for cat_id, cat_info in CATEGORIES.items():
        if cat_id == 'etc':
            continue
        for keyword in cat_info['keywords']:
            if keyword in text:
                return cat_id
    
    return 'etc'


def generate_html(services: List[Dict]) -> str:
    """HTML 생성 (탭 + 드롭다운)"""
    now = datetime.now()
    update_time = now.strftime('%Y-%m-%d %H:%M')
    
    # 카테고리별 분류
    categorized = {cat: [] for cat in CATEGORY_ORDER}
    for svc in services:
        cat = categorize_service(svc)
        categorized[cat].append(svc)
    
    # JSON 데이터 생성
    json_data = {
        'updateTime': update_time,
        'total': len(services)
    }
    
    for cat_id in CATEGORY_ORDER:
        cat_services = categorized[cat_id][:15]  # 최대 15개
        items = []
        
        for svc in cat_services:
            items.append({
                'name': svc.get('서비스명', ''),
                'org': svc.get('소관기관명', ''),
                'target': svc.get('지원대상', '')[:100] if svc.get('지원대상') else '',
                'content': svc.get('지원내용', '')[:200] if svc.get('지원내용') else '',
                'method': svc.get('신청방법', '')[:100] if svc.get('신청방법') else '',
                'period': svc.get('신청기한', '') or '상시',
                'url': svc.get('상세조회URL', ''),
                'phone': svc.get('전화문의', '') or ''
            })
        
        json_data[cat_id] = {
            'count': len(categorized[cat_id]),
            'items': items
        }
    
    # 카테고리 정보 JSON
    cat_info_json = {cat_id: {'name': info['name'], 'icon': info['icon'], 'color': info['color'], 'bg': info['bg']} 
                     for cat_id, info in CATEGORIES.items()}
    
    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>정부 지원금·보조금 안내</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: #1a1a1a; }}
        ::-webkit-scrollbar-thumb {{ background: #444; border-radius: 4px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #555; }}
        html {{ scrollbar-width: thin; scrollbar-color: #444 #1a1a1a; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Malgun Gothic', sans-serif;
            background: #0a0a0a;
            color: #e5e5e5;
            line-height: 1.5;
            padding: 12px;
        }}
        .tabs {{
            display: flex;
            gap: 4px;
            margin-bottom: 12px;
            overflow-x: auto;
            padding-bottom: 4px;
        }}
        .tab {{
            flex-shrink: 0;
            padding: 8px 12px;
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            color: #888;
            font-size: 12px;
            font-weight: 600;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .tab:hover {{ border-color: #555; }}
        .tab.active {{
            background: linear-gradient(135deg, #1e40af, #1e3a8a);
            border-color: #3b82f6;
            color: #fff;
        }}
        .tab .icon {{ font-size: 14px; display: block; margin-bottom: 2px; }}
        .tab .count {{ font-size: 14px; font-weight: 700; display: block; margin-top: 2px; }}
        .header {{
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 12px;
            text-align: center;
        }}
        .header h1 {{ font-size: 16px; margin-bottom: 4px; color: #fff; }}
        .header p {{ font-size: 11px; color: rgba(255,255,255,0.6); }}
        .header .stat {{
            display: inline-block;
            margin-top: 12px;
            background: rgba(0,0,0,0.3);
            padding: 8px 20px;
            border-radius: 8px;
        }}
        .header .stat-num {{ font-size: 20px; font-weight: 700; }}
        .header .stat-lbl {{ font-size: 10px; color: rgba(255,255,255,0.5); }}
        .list {{ display: flex; flex-direction: column; gap: 8px; }}
        .card {{
            background: #141414;
            border: 1px solid #252525;
            border-radius: 10px;
            overflow: hidden;
            cursor: pointer;
            transition: border-color 0.2s;
        }}
        .card:hover {{ border-color: #444; }}
        .card-main {{ padding: 14px; }}
        .card-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 10px;
            margin-bottom: 6px;
        }}
        .card-name {{
            font-size: 14px;
            font-weight: 600;
            color: #fff;
            flex: 1;
        }}
        .card-org {{
            font-size: 10px;
            color: #888;
            background: #252525;
            padding: 2px 8px;
            border-radius: 4px;
            flex-shrink: 0;
        }}
        .card-target {{
            font-size: 12px;
            color: #888;
            display: -webkit-box;
            -webkit-line-clamp: 1;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .card-arrow {{
            float: right;
            color: #555;
            transition: transform 0.3s;
            margin-top: -20px;
        }}
        .card.open .card-arrow {{ transform: rotate(180deg); }}
        .card-detail {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
            background: #0f0f0f;
        }}
        .card.open .card-detail {{ max-height: 500px; }}
        .card-detail-inner {{
            padding: 14px;
            border-top: 1px solid #222;
        }}
        .detail-section {{
            margin-bottom: 12px;
        }}
        .detail-section:last-child {{ margin-bottom: 0; }}
        .detail-label {{
            font-size: 11px;
            color: #666;
            margin-bottom: 4px;
        }}
        .detail-value {{
            font-size: 13px;
            color: #bbb;
            line-height: 1.6;
        }}
        .detail-link {{
            display: inline-block;
            margin-top: 12px;
            padding: 8px 16px;
            background: #1e40af;
            color: #fff;
            text-decoration: none;
            border-radius: 6px;
            font-size: 12px;
        }}
        .footer {{
            text-align: center;
            padding: 16px 0 8px;
            font-size: 10px;
            color: #444;
        }}
        .footer a {{ color: #60a5fa; text-decoration: none; }}
        .empty {{
            text-align: center;
            padding: 40px 20px;
            color: #555;
            font-size: 13px;
        }}
        .content {{ display: none; }}
        .content.active {{ display: block; }}
    </style>
</head>
<body>
    <div class="tabs" id="tabs"></div>
    <div id="contents"></div>
    <div class="footer">
        자료: <a href="https://www.gov.kr/portal/rcvfvrSvc/main" target="_blank">정부24 보조금24</a><br>
        업데이트: <span id="update-time"></span>
    </div>

    <script>
        const DATA = {json.dumps(json_data, ensure_ascii=False)};
        const CATS = {json.dumps(cat_info_json, ensure_ascii=False)};
        const ORDER = {json.dumps(CATEGORY_ORDER)};
        
        let currentTab = ORDER[0];
        
        function switchTab(tabId) {{
            currentTab = tabId;
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelector(`.tab[data-id="${{tabId}}"]`).classList.add('active');
            document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
            document.getElementById(`content-${{tabId}}`).classList.add('active');
        }}
        
        function toggleCard(card) {{
            const wasOpen = card.classList.contains('open');
            document.querySelectorAll('.card.open').forEach(c => c.classList.remove('open'));
            if (!wasOpen) {{
                card.classList.add('open');
                setTimeout(() => card.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }}), 100);
            }}
        }}
        
        function renderTabs() {{
            const tabsEl = document.getElementById('tabs');
            let html = '';
            
            ORDER.forEach(catId => {{
                const cat = CATS[catId];
                const count = DATA[catId]?.count || 0;
                html += `
                    <div class="tab" data-id="${{catId}}" onclick="switchTab('${{catId}}')">
                        <span class="icon">${{cat.icon}}</span>
                        ${{cat.name}}
                        <span class="count">${{count}}</span>
                    </div>
                `;
            }});
            
            tabsEl.innerHTML = html;
        }}
        
        function renderContents() {{
            const contentsEl = document.getElementById('contents');
            let html = '';
            
            ORDER.forEach((catId, idx) => {{
                const cat = CATS[catId];
                const data = DATA[catId] || {{ count: 0, items: [] }};
                const isActive = idx === 0 ? 'active' : '';
                
                html += `
                    <div id="content-${{catId}}" class="content ${{isActive}}">
                        <div class="header" style="background: linear-gradient(135deg, ${{cat.bg}}, #0f0f0f); border: 1px solid ${{cat.color}}40;">
                            <h1>${{cat.icon}} ${{cat.name}} 지원사업</h1>
                            <p>여주시민이 받을 수 있는 ${{cat.name}} 지원 혜택</p>
                            <div class="stat">
                                <div class="stat-num" style="color:${{cat.color}}">${{data.count}}건</div>
                                <div class="stat-lbl">지원사업</div>
                            </div>
                        </div>
                        <div class="list">
                `;
                
                if (data.items.length === 0) {{
                    html += '<div class="empty">해당 카테고리의 지원사업이 없습니다</div>';
                }} else {{
                    data.items.forEach(item => {{
                        html += `
                            <div class="card" onclick="toggleCard(this)">
                                <div class="card-main">
                                    <div class="card-top">
                                        <div class="card-name">${{item.name}}</div>
                                        <div class="card-org">${{item.org}}</div>
                                    </div>
                                    <div class="card-target">👤 ${{item.target || '전체'}}</div>
                                    <div class="card-arrow">▼</div>
                                </div>
                                <div class="card-detail">
                                    <div class="card-detail-inner">
                                        <div class="detail-section">
                                            <div class="detail-label">지원대상</div>
                                            <div class="detail-value">${{item.target || '-'}}</div>
                                        </div>
                                        <div class="detail-section">
                                            <div class="detail-label">지원내용</div>
                                            <div class="detail-value">${{item.content || '-'}}</div>
                                        </div>
                                        <div class="detail-section">
                                            <div class="detail-label">신청방법</div>
                                            <div class="detail-value">${{item.method || '-'}}</div>
                                        </div>
                                        <div class="detail-section">
                                            <div class="detail-label">신청기한</div>
                                            <div class="detail-value">${{item.period || '상시'}}</div>
                                        </div>
                                        ${{item.phone ? `
                                        <div class="detail-section">
                                            <div class="detail-label">문의전화</div>
                                            <div class="detail-value">${{item.phone}}</div>
                                        </div>
                                        ` : ''}}
                                        ${{item.url ? `<a class="detail-link" href="${{item.url}}" target="_blank">정부24에서 신청하기 →</a>` : ''}}
                                    </div>
                                </div>
                            </div>
                        `;
                    }});
                }}
                
                html += '</div></div>';
            }});
            
            contentsEl.innerHTML = html;
        }}
        
        function init() {{
            document.getElementById('update-time').textContent = DATA.updateTime;
            renderTabs();
            renderContents();
            document.querySelector('.tab').classList.add('active');
        }}
        
        init();
    </script>
</body>
</html>'''
    
    return html


def create_thumbnail(counts: Dict, output_path: str = "thumbnail.png"):
    """섬네일 이미지 생성"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  Pillow 없음 - 섬네일 생략")
        return None
    
    width, height = 1200, 630
    img = Image.new('RGB', (width, height), '#0a1628')
    draw = ImageDraw.Draw(img)
    
    # 그라데이션 배경
    for y in range(height):
        r = int(10 + (y / height) * 15)
        g = int(22 + (y / height) * 10)
        b = int(40 + (y / height) * 20)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    # 장식
    draw.ellipse([(-150, -150), (250, 250)], fill='#1e3a5f')
    draw.ellipse([(950, 450), (1350, 850)], fill='#1e3a5f')
    
    # 폰트
    try:
        font_bold_lg = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf", 58)
        font_bold_md = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf", 40)
        font_count = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf", 36)
        font_label = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumSquareRoundR.ttf", 20)
    except:
        print("  폰트 없음 - 섬네일 생략")
        return None
    
    now = datetime.now()
    
    # 아이콘
    draw.text((100, 130), "📢", font=font_bold_lg, fill='#ffffff', anchor='mm')
    
    # 타이틀
    draw.text((width//2 + 30, 130), "정부 지원금·보조금 안내", font=font_bold_lg, fill='#ffffff', anchor='mm')
    draw.text((width//2, 200), f"{now.month}월 지원사업 현황", font=font_bold_md, fill='#60a5fa', anchor='mm')
    
    # 구분선
    draw.line([(200, 250), (1000, 250)], fill='#334155', width=1)
    
    # 카테고리 박스
    box_y = 300
    box_h = 140
    box_w = 160
    gap = 20
    
    categories = [
        ("청년", counts.get('youth', 0), "#60a5fa", "#1e3a5f"),
        ("노인", counts.get('senior', 0), "#c084fc", "#4a1d6a"),
        ("출산/육아", counts.get('family', 0), "#f472b6", "#831843"),
        ("장애인", counts.get('disabled', 0), "#4ade80", "#14532d"),
        ("저소득", counts.get('lowincome', 0), "#fbbf24", "#713f12"),
        ("소상공인", counts.get('business', 0), "#fb923c", "#7c2d12"),
    ]
    
    start_x = (width - (box_w * 6 + gap * 5)) // 2
    
    for i, (label, count, color, bg) in enumerate(categories):
        x = start_x + i * (box_w + gap)
        draw.rounded_rectangle([x, box_y, x+box_w, box_y+box_h], radius=12, fill=bg, outline=color, width=2)
        draw.text((x + box_w//2, box_y + 40), label, font=font_label, fill='#aaaaaa', anchor='mm')
        draw.text((x + box_w//2, box_y + 90), f"{count}건", font=font_count, fill=color, anchor='mm')
    
    # 하단
    draw.text((width//2, 520), "여주소식", font=font_bold_md, fill='#555555', anchor='mm')
    draw.text((width//2, 570), "yjgood.kr", font=font_label, fill='#444444', anchor='mm')
    
    img.save(output_path, 'PNG', quality=95)
    print(f"  ✅ 섬네일: {output_path}")
    return output_path


def upload_media(file_path: str):
    """워드프레스에 이미지 업로드"""
    if not all([WP_URL, WP_USER, WP_APP_PASSWORD]):
        return None, None
    
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        filename = os.path.basename(file_path)
        response = requests.post(
            f"{WP_URL}/wp-json/wp/v2/media",
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'image/png'
            },
            data=file_data,
            auth=(WP_USER, WP_APP_PASSWORD),
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result.get('id'), result.get('source_url')
    except Exception as e:
        print(f"  미디어 업로드 실패: {e}")
        return None, None


def post_to_wordpress(title: str, content: str, category_id: int = None, thumbnail_id: int = None) -> bool:
    """워드프레스에 발행"""
    if not all([WP_URL, WP_USER, WP_APP_PASSWORD]):
        with open("index.html", 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✅ HTML 저장: index.html")
        return False
    
    post_data = {
        'title': title,
        'content': content,
        'status': 'publish'
    }
    
    if category_id:
        post_data['categories'] = [category_id]
    if thumbnail_id:
        post_data['featured_media'] = thumbnail_id
    
    try:
        response = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts",
            json=post_data,
            auth=(WP_USER, WP_APP_PASSWORD),
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        print(f"  ✅ 발행: {result.get('link', '')}")
        return True
    except Exception as e:
        print(f"  발행 실패: {e}")
        return False


def main():
    print("📢 정부 지원금/보조금 정보 업데이트 시작...")
    
    # 서비스 목록 조회
    print("  서비스 목록 조회 중...")
    all_services = fetch_all_services(max_pages=15)
    print(f"  전체 서비스: {len(all_services)}건")
    
    # 여주시/경기도/전국 필터링
    services = filter_local_services(all_services)
    print(f"  여주시민 대상: {len(services)}건")
    
    if not services:
        print("해당 서비스 없음")
        return
    
    # 카테고리별 카운트
    counts = {cat: 0 for cat in CATEGORY_ORDER}
    for svc in services:
        cat = categorize_service(svc)
        counts[cat] += 1
    
    for cat_id, count in counts.items():
        if count > 0:
            print(f"    {CATEGORIES[cat_id]['name']}: {count}건")
    
    # HTML 생성
    html_content = generate_html(services)
    
    # index.html 저장 (GitHub Pages용)
    with open("index.html", 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("  ✅ index.html 생성")
    
    # 섬네일 생성
    thumb_path = create_thumbnail(counts, "thumbnail.png")
    
    # 워드프레스 발행
    now = datetime.now()
    title = f"{now.month}월 정부 지원금·보조금 안내 ({len(services)}건)"
    
    # iframe 콘텐츠
    iframe_content = f'''
<iframe src="https://leekkyg.github.io/subsidy-bot/" width="100%" height="800" style="border:none; border-radius:12px; max-width:600px;" loading="lazy"></iframe>

<p style="font-size:12px; color:#666; margin-top:16px;">※ {now.month}월 {now.day}일 기준 업데이트<br>자료 출처: 정부24 보조금24</p>
'''
    
    # 섬네일 업로드
    thumb_id = None
    if thumb_path and os.path.exists(thumb_path):
        thumb_id, thumb_url = upload_media(thumb_path)
        if thumb_id:
            print(f"  ✅ 섬네일 업로드: {thumb_url}")
    
    post_to_wordpress(title, iframe_content, category_id=139, thumbnail_id=thumb_id)
    
    print("✅ 완료!")


if __name__ == '__main__':
    main()
