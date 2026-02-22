import urllib.request
import urllib.parse
import json
import os
import re

# GitHub Secrets에서 가져올 환경 변수
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# GitHub repo 내부 저장소(이전 발송 기록 보관용)
HISTORY_FILE = "history.json"

def get_html(url):
    """
    Python 기본 라이브러리를 사용해 User-Agent를 붙여서 HTML을 가져옴
    """
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    try:
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"HTML 가져오기 실패: {url} - {e}")
        return ""

def parse_edu_list(html_text):
    """정규표현식을 사용해 HTML 텍스트 내의 공고 정보 추출"""
    results = []
    
    # <li> 블록 추출
    li_matches = re.findall(r'<div class="card-box">(.*?)</div>\s*</a>\s*</li>', html_text, re.DOTALL | re.IGNORECASE)
    
    for card_html in li_matches:
        # 제목 정보
        title_match = re.search(r'<span class="title">\s*(.*?)\s*</span>', card_html, re.DOTALL)
        title = title_match.group(1).strip() if title_match else "무제"
        
        # 지점 정보
        branch_match = re.search(r'<span class="info1">\s*(.*?)\s*</span>', card_html, re.DOTALL)
        branch = branch_match.group(1).strip() if branch_match else "지점 불명"
        
        # 교육 기간
        date_match = re.search(r'<span class="info2">\s*(.*?)\s*</span>', card_html, re.DOTALL)
        date = date_match.group(1).strip() if date_match else "기간 미정"
        
        # 신청 상태 (접수중, 신청마감 등)
        state_match = re.search(r'<button type="button".*?>(.*?)</button>', card_html, re.DOTALL)
        state = state_match.group(1).strip() if state_match else "상태 없음"
        
        # 고유 번호 (eduno) - 버튼이나 데이터에서 추출
        id_match = re.search(r'eduno=(\d+)', card_html)
        eduno = id_match.group(1) if id_match else ""
        
        if eduno:
            results.append({
                "eduno": eduno,
                "title": title,
                "branch": branch,
                "date": date,
                "state": state
            })
            
    return results

def send_telegram_message(message):
    """Telegram API를 통해 메시지 발송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("경고: 텔레그램 토큰 또는 챗 아이디가 설정되지 않았습니다.")
        return False
        
        print(f"DEBUG: 현재 사용중인 토큰 시작부분 -> {TELEGRAM_BOT_TOKEN[:5]}")
        print(f"DEBUG: 현재 사용중인 챗아이디 -> {TELEGRAM_CHAT_ID}")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    data = urllib.parse.urlencode(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data)
    
    try:
        with urllib.request.urlopen(req) as response:
            return True
    except Exception as e:
        print(f"텔레그램 발송 오류: {e}")
        return False

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def run():
    print("GitHub Actions: 대한적십자사 교육 공고 스크래핑 시작...")
    
    url_08 = "https://www.redcross.or.kr/learn/edu/edu_card.do?educode1=01&educode2=08"
    url_23 = "https://www.redcross.or.kr/learn/edu/edu_card.do?educode1=01&educode2=23"
    
    html_08 = get_html(url_08)
    html_23 = get_html(url_23)
    
    list_08 = parse_edu_list(html_08)
    list_23 = parse_edu_list(html_23)
    
    all_edus = list_08 + list_23
    history = load_history()
    new_found = False
    
    for edu in all_edus:
        if edu["eduno"] in history:
            continue
            
        # 신청 가능 상태가 아니면 알림 제외
        if "신청" not in edu["state"] or "마감" in edu["state"]:
             continue
             
        msg = (
            f"🚨 <b>대한적십자사 교육 신규 공고</b>\n\n"
            f"📍 <b>지부</b>: {edu['branch']}\n"
            f"📝 <b>과정명</b>: {edu['title']}\n"
            f"📅 <b>교육기간</b>: {edu['date']}\n\n"
            f"🔗 <a href='https://www.redcross.or.kr/learn/edu/edu_view.do?eduno={edu['eduno']}'>상세보기 및 신청 (클릭)</a>"
        )
        
        success = send_telegram_message(msg)
        if success:
            print(f"[발송 성공] {edu['branch']} - {edu['title']}")
            history.append(edu["eduno"])
            new_found = True
            
    if new_found:
        save_history(history)
        print("히스토리 업데이트 완료.")
    else:
        print("새로 업데이트된 공고가 없습니다.")

if __name__ == "__main__":
    run()

