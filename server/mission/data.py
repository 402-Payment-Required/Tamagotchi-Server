MISSION_META = {
    "kiosk_cafe": {"title": "카페 키오스크 주문", "type": "kiosk"},
    "typing_1": {"title": "문자 따라 쓰기", "type": "typing"},
    "sms_greeting": {"title": "손주에게 안부 문자 보내기", "type": "sms"},
}

MISSIONS = {
    "kiosk_cafe": [
        {
            "step": 0,
            "prompt": "매장에서 드시나요, 포장하시나요?",
            "options": ["매장에서 먹기", "포장하기"],
            "answer": "매장에서 먹기",
            "hint": "큰 버튼 '매장에서 먹기'를 눌러보세요",
        },
        {
            "step": 1,
            "prompt": "메뉴를 골라주세요",
            "options": ["아메리카노", "카페라떼"],
            "answer": "아메리카노",
            "hint": "첫 번째 버튼 '아메리카노'를 눌러보세요",
        },
        {
            "step": 2,
            "prompt": "포인트 적립하시겠어요?",
            "options": ["예", "아니오"],
            "answer": "아니오",
            "hint": "'아니오'를 눌러보세요",
            "final": True,
        },
    ],
    "typing_1": [
        {
            "step": 0,
            "prompt": "이 문장을 그대로 입력해보세요: '오늘 날씨가 좋네요'",
            "options": [],
            "answer": "오늘 날씨가 좋네요",
            "hint": "띄어쓰기까지 똑같이 입력해보세요",
            "final": True,
        },
    ],
    "sms_greeting": [
        {
            "step": 0,
            "prompt": "받는 사람을 골라주세요",
            "options": ["손주", "손녀", "친구"],
            "answer": "손주",
            "hint": "제일 위 '손주' 버튼을 눌러보세요",
        },
        {
            "step": 1,
            "prompt": "보낼 내용을 골라주세요",
            "options": ["오늘 밥 잘 먹었니", "사랑한다"],
            "answer": "오늘 밥 잘 먹었니",
            "hint": "'오늘 밥 잘 먹었니'를 골라보세요",
        },
        {
            "step": 2,
            "prompt": "정말 보내시겠어요?",
            "options": ["보내기", "취소"],
            "answer": "보내기",
            "hint": "'보내기' 버튼을 눌러보세요",
            "final": True,
        },
    ],
}
