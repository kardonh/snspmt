const instagramDetailedServices = {
    popular_posts: [
      // 기존 서비스들
      { id: 361, name: '🥇인기게시물 상위 노출[🎨사진] TI1', price: 3000000, min: 1, max: 10, time: '6 시간 10 분' },
      { id: 444, name: '🥇인기게시물 상위 노출 유지[🎨사진] TI1-1', price: 90000, min: 100, max: 3000, time: '데이터가 충분하지 않습니다' },
      { id: 435, name: '🥇인기게시물 상위 노출[🎬릴스] TV1', price: 12000000, min: 1, max: 10, time: '23 시간 32 분' },
      { id: 443, name: '🥇인기게시물 상위 노출[🎨사진] TI2', price: 27000, min: 100, max: 500, time: '16 분' },
      { id: 445, name: '🥇인기게시물 상위 노출 유지[🎨사진] TI2-1', price: 90000, min: 100, max: 3000, time: '데이터가 충분하지 않습니다' },
      { id: 332, name: '0️⃣.[준비단계]:최적화 계정 준비', price: 0, min: 1, max: 1, time: '데이터가 충분하지 않습니다' },
      { id: 325, name: '1️⃣.[상승단계]:리얼 한국인 좋아요 유입', price: 19500, min: 100, max: 10000, time: '데이터가 충분하지 않습니다' },
      { id: 326, name: '2️⃣.[상승단계]:리얼 한국인 댓글 유입', price: 225000, min: 10, max: 300, time: '데이터가 충분하지 않습니다' },
      { id: 327, name: '3️⃣.[상승단계]:파워 외국인 좋아요 유입', price: 1800, min: 100, max: 200000, time: '데이터가 충분하지 않습니다' },
      { id: 328, name: '4️⃣.[등록단계]:파워 게시물 저장 유입', price: 315, min: 100, max: 1000000, time: '1 시간 52 분' },
      { id: 329, name: '5️⃣.[등록단계]:파워 게시물 노출 + 도달 + 홈 유입', price: 450, min: 1000, max: 1000000, time: '데이터가 충분하지 않습니다' },
      { id: 330, name: '6️⃣.[유지단계]:파워 게시물 저장 [✔연속 유입] 작업', price: 300, min: 100, max: 1000000, time: '7 시간 5 분' },
      { id: 331, name: '7️⃣.[유지단계]:게시물 노출+도달+홈 [✔연속 유입] 작업', price: 450, min: 100, max: 1000000, time: '데이터가 충분하지 않습니다' }
    ],
    
    // 한국인 패키지 서비스
    korean_package: [
      // 🎯 추천탭 상위노출 (내계정) - 진입단계
      { id: 1003, name: '🎯 추천탭 상위노출 (내계정) - 진입단계 [4단계 패키지]', price: 20000000, min: 1, max: 1, time: '24-48시간', description: '진입단계 4단계 완전 패키지', package: true, steps: [
        { id: 122, name: '1단계: 실제 한국인 게시물 좋아요 [진입 단계]', quantity: 300, delay: 0, description: '🇰🇷 인스타그램 한국인 💎💎파워업 좋아요💖💖[💪인.게 최적화↑]' },
        { id: 329, name: '2단계: 파워 게시물 노출 + 도달 + 기타 유입', quantity: 10000, delay: 10, description: '5️⃣:[등록단계]파워게시물 노출 + 도달 + 홈 유입' },
        { id: 328, name: '3단계: 파워 게시물 저장 유입', quantity: 1000, delay: 10, description: '4️⃣[등록단계]파워 게시물 저장 유입' },
        { id: 342, name: '4단계: KR 인스타그램 리얼 한국인 랜덤 댓글', quantity: 5, delay: 10, description: '🇰🇷 인스타그램 리얼 한국인 랜덤 댓글💬' }
      ]},
      
      // 🎯 추천탭 상위노출 (내계정) - 유지단계
      { id: 1004, name: '🎯 추천탭 상위노출 (내계정) - 유지단계 [2단계 패키지]', price: 15000000, min: 1, max: 1, time: '15시간', description: '유지단계 2단계 완전 패키지 (90분 간격)', package: true, steps: [
        { id: 325, name: '1단계: 실제 한국인 게시물 좋아요 [90분당 100개씩 10회]', quantity: 100, delay: 90, repeat: 10, description: '[상승단계]:리얼 한국인 좋아요 - 90분 간격 10회 반복' },
        { id: 331, name: '2단계: 게시물 노출+도달+홈 [90분당 200개씩 10회]', quantity: 200, delay: 90, repeat: 10, description: '[유지단계]:게시물 노출+도달+홈 - 90분 간격 10회 반복' }
      ]},
      
      // 인스타 계정 상위노출 [30일] - Drip-feed 방식 사용 (runs: 30, interval: 1440)
      { id: 1005, name: '인스타 계정 상위노출 [30일]', price: 150000000, min: 1, max: 1, time: '30일', description: '인스타그램 프로필 방문 하루 400개씩 30일간', smmkings_id: 515, drip_feed: true, runs: 30, interval: 1440, drip_quantity: 400 }
    ],
    
    // 커스텀/이모지 댓글 서비스
    custom_comments_korean: [
      { id: 339, name: 'KR 인스타그램 한국인 커스텀 댓글', price: 400000, min: 5, max: 500, time: '6분', description: '상세정보' },
      { id: 340, name: 'KR 인스타그램 한국인 커스텀 댓글 [여자]', price: 500000, min: 5, max: 500, time: '데이터 부족', description: '상세정보' },
      { id: 341, name: 'KR 인스타그램 한국인 커스텀 댓글 [남자]', price: 500000, min: 5, max: 500, time: '6분', description: '상세정보' },
      { id: 291, name: 'KR 인스타그램 한국인 이모지 댓글', price: 260000, min: 5, max: 1000, time: '데이터 부족', description: '상세정보' }
    ],
    
    // 릴스 조회수 서비스
    reels_views_korean: [
      { id: 111, name: 'KR 인스타그램 리얼 한국인 동영상 조회수', price: 2000, min: 100, max: 2147483647, time: '20시간 33분', description: '상세정보' }
    ],
    
    // 자동 팔로워 서비스
    auto_followers: [
      { id: 369, name: 'KR 인스타그램 한국인 💎 슈퍼프리미엄 자동 좋아요', price: 30000, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' }
    ],
    
    // 자동 리그램 서비스
    auto_regram: [
      { id: 305, name: 'KR 인스타그램 한국인 리그램', price: 450000, min: 3, max: 3000, time: '6시간 12분', description: '상세정보' }
    ],
    
    
    likes_korean: [
      { id: 122, name: 'KR 인스타그램 한국인 ❤️ 파워업 좋아요', price: 20000, min: 30, max: 2500, time: '14시간 54분', description: '상세정보' },
      { id: 333, name: 'KR 인스타그램 한국인 ❤️ 슈퍼프리미엄 좋아요', price: 30000, min: 100, max: 1000, time: '데이터 부족', description: '상세정보' },
      { id: 276, name: 'KR 인스타그램 리얼 한국인 [여자] 좋아요', price: 30000, min: 30, max: 5000, time: '9분', description: '상세정보' },
      { id: 275, name: 'KR 인스타그램 리얼 한국인 [남자] 좋아요', price: 30000, min: 30, max: 5000, time: '10분', description: '상세정보' },
      { id: 277, name: 'KR 인스타그램 리얼 한국인 [20대] 좋아요', price: 30000, min: 30, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 280, name: 'KR 인스타그램 리얼 한국인 [20대여자] 좋아요', price: 40000, min: 30, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 279, name: 'KR 인스타그램 리얼 한국인 [20대남자] 좋아요', price: 40000, min: 30, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 278, name: 'KR 인스타그램 리얼 한국인 [30대] 좋아요', price: 30000, min: 30, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 282, name: 'KR 인스타그램 리얼 한국인 [30대여자] 좋아요', price: 40000, min: 30, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 281, name: 'KR 인스타그램 리얼 한국인 [30대남자] 좋아요', price: 40000, min: 30, max: 2500, time: '데이터 부족', description: '상세정보' }
    ],
    followers_korean: [
      { id: 491, name: 'KR 인스타그램 💯 리얼 한국인 팔로워 [일반]', price: 160000, min: 10, max: 1000, time: '데이터 부족', description: '상세정보' },
      { id: 334, name: 'KR 인스타그램 💯 리얼 한국인 팔로워 [디럭스]', price: 210000, min: 10, max: 40000, time: '1시간 3분', description: '상세정보' },
      { id: 383, name: 'KR 인스타그램 💯 리얼 한국인 팔로워 [프리미엄]', price: 270000, min: 10, max: 40000, time: '1시간 3분', description: '상세정보' }

    ],
    views: [
      { id: 111, name: 'KR 인스타그램 리얼 한국인 동영상 조회수', price: 2000, min: 100, max: 2147483647, time: '20시간 33분', description: '상세정보' },
      { id: 109, name: '인스타그램 동영상 조회수 [REEL/IGTV/VIDEO 가능]', price: 300, min: 100, max: 1000000, time: '데이터 부족' },
      { id: 382, name: '인스타그램 동영상 조회수+저장+시간', price: 1200, min: 100, max: 1000000, time: '데이터 부족' },
      { id: 515, name: '인스타그램 프로필 방문', price: 1000, min: 10, max: 10000, time: '데이터 부족' },
      { id: 374, name: 'KR 인스타그램 한국인 노출 [+도달+기타]', price: 8000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
      { id: 141, name: 'KR 인스타그램 리얼 한국인 저장', price: 40000, min: 10, max: 1000000, time: '2분', description: '상세정보' },
      { id: 305, name: 'KR 인스타그램 한국인 리그램', price: 450000, min: 3, max: 3000, time: '6시간 12분', description: '상세정보' }
    ],
    comments_korean: [
      { id: 342, name: 'KR 인스타그램 리얼 한국인 랜덤 댓글', price: 260000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 297, name: 'KR 인스타그램 리얼 한국인 랜덤 댓글 [여자]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 296, name: 'KR 인스타그램 리얼 한국인 랜덤 댓글 [남자]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 298, name: 'KR 인스타그램 리얼 한국인 랜덤 댓글 [20대]', price: 260000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 299, name: 'KR 인스타그램 리얼 한국인 랜덤 댓글 [20대여자]', price: 400000, min: 5, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 300, name: 'KR 인스타그램 리얼 한국인 랜덤 댓글 [20대남자]', price: 400000, min: 5, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 301, name: 'KR 인스타그램 리얼 한국인 랜덤 댓글 [30대]', price: 260000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 302, name: 'KR 인스타그램 리얼 한국인 랜덤 댓글 [30대여자]', price: 400000, min: 5, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 303, name: 'KR 인스타그램 리얼 한국인 랜덤 댓글 [30대남자]', price: 400000, min: 5, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 291, name: 'KR 인스타그램 한국인 이모지 댓글', price: 260000, min: 5, max: 1000, time: '데이터 부족', description: '상세정보' },
      { id: 339, name: 'KR 인스타그램 한국인 커스텀 댓글', price: 400000, min: 5, max: 500, time: '6분', description: '상세정보' },
      { id: 340, name: 'KR 인스타그램 한국인 커스텀 댓글 [여자]', price: 500000, min: 5, max: 500, time: '데이터 부족', description: '상세정보' },
      { id: 341, name: 'KR 인스타그램 한국인 커스텀 댓글 [남자]', price: 500000, min: 5, max: 500, time: '6분', description: '상세정보' }
    ],
    regram_korean: [
      { id: 305, name: '🇰🇷 인스타그램 한국인 리그램🎯', price: 375000, min: 3, max: 3000, time: '7 시간 21 분' }
    ],
    exposure_save_share: [
      { id: 142, name: '인스타그램 노출(+도달+추+프로필+기타)', price: 2500, min: 100, max: 1000000, time: '데이터 부족' },
      { id: 145, name: '인스타그램 노출(+도달+추+프로필+기타)', price: 5000, min: 100, max: 1000000, time: '데이터 부족' },
      { id: 312, name: '인스타그램 저장', price: 500, min: 10, max: 10000, time: '데이터 부족' },
      { id: 313, name: '인스타그램 공유', price: 8000, min: 10, max: 10000, time: '데이터 부족' }
    ],

    auto_likes: [
      { id: 348, name: 'KR 인스타그램 한국인 ❤️ 파워업 좋아요', price: 19000, min: 30, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 369, name: 'KR 인스타그램 한국인 💎 슈퍼프리미엄 자동 좋아요', price: 30000, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' }
    ],
    auto_views: [
      { id: 349, name: '인스타그램 동영상 자동 조회수', price: 6000, min: 100, max: 2147483647, time: '데이터 부족', description: '상세정보' }
    ],
    auto_comments: [
      { id: 350, name: 'KR 인스타그램 한국인 자동 랜덤 댓글', price: 260000, min: 3, max: 100, time: '10분', description: '상세정보' }
    ],

    // 스레드 세부 서비스 데이터
    threads: {
      likes_korean: [
        { id: 453, name: 'KR Threads 한국인 리얼 좋아요', price: 22000, min: 50, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 454, name: 'KR Threads 한국인 리얼 팔로워', price: 95000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 457, name: 'KR Threads 한국인 리얼 댓글', price: 270000, min: 5, max: 500, time: '데이터 부족', description: '상세정보' },
        { id: 498, name: 'KR Threads 한국인 리얼 공유', price: 450000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' }
      ]
    },

    // 인스타그램 외국인 서비스 데이터
    foreign_package: [
      
    ],
    followers_foreign: [
      { id: 475, name: '인스타그램 외국인 팔로워', price: 10000, min: 100, max: 10000, time: '데이터 부족', description: '외국인 팔로워 서비스' }
    ],
    likes_foreign: [
      { id: 105, name: '인스타그램 외국인 좋아요', price: 5000, min: 50, max: 10000, time: '데이터 부족', description: '외국인 좋아요 서비스' },
      { id: 116, name: '인스타그램 리얼 외국인 좋아요', price: 7000, min: 50, max: 10000, time: '데이터 부족', description: '리얼 외국인 좋아요 서비스' }
    ],
    comments_foreign: [
      { id: 480, name: '인스타그램 외국인 랜덤 댓글', price: 50000, min: 20, max: 1000, time: '데이터 부족', description: '외국인 랜덤 댓글 서비스' },
      { id: 481, name: '인스타그램 외국인 커스텀 댓글', price: 60000, min: 20, max: 1000, time: '데이터 부족', description: '외국인 커스텀 댓글 서비스' },
      { id: 358, name: '인스타그램 외국인 랜덤 이모지 댓글', price: 50000, min: 20, max: 1000, time: '데이터 부족', description: '외국인 랜덤 이모지 댓글 서비스' }
    ],
    reels_views_foreign: [
      { id: 109, name: '인스타그램 동영상 조회수 [REEL/IGTV/VIDEO 가능]', price: 300, min: 100, max: 1000000, time: '데이터 부족', description: '동영상 조회수 서비스' },
      { id: 382, name: '인스타그램 동영상 조회수+저장+시간', price: 1200, min: 100, max: 1000000, time: '데이터 부족', description: '동영상 조회수+저장+시간 서비스' }
    ],
    exposure_save_share_foreign: [
      { id: 515, name: '인스타그램 프로필 방문', price: 1000, min: 10, max: 10000, time: '데이터 부족', description: '프로필 방문 서비스' },
      { id: 142, name: '인스타그램 노출(+도달+추+프로필+기타)', price: 2500, min: 100, max: 1000000, time: '데이터 부족', description: '노출+도달+추+프로필+기타 서비스' },
      { id: 145, name: '인스타그램 노출(+도달+추+프로필+기타)', price: 5000, min: 100, max: 1000000, time: '데이터 부족', description: '노출+도달+추+프로필+기타 서비스' },
      { id: 312, name: '인스타그램 저장', price: 500, min: 10, max: 10000, time: '데이터 부족', description: '저장 서비스' },
      { id: 313, name: '인스타그램 공유', price: 8000, min: 10, max: 10000, time: '데이터 부족', description: '공유 서비스' }
      ],
      live_streaming: [
      { id: 393, name: '인스타그램 실시간 라이브 스트리밍 시청 [15분]', price: 3000, min: 10, max: 10000, time: '데이터 부족', description: '실시간 라이브 스트리밍 시청 서비스' },
      { id: 394, name: '인스타그램 실시간 라이브 스트리밍 시청 [30분]', price: 6000, min: 10, max: 10000, time: '데이터 부족', description: '실시간 라이브 스트리밍 시청 서비스' },
      { id: 395, name: '인스타그램 실시간 라이브 스트리밍 시청 [60분]', price: 12000, min: 10, max: 10000, time: '데이터 부족', description: '실시간 라이브 스트리밍 시청 서비스' },
      { id: 396, name: '인스타그램 실시간 라이브 스트리밍 시청 [90분]', price: 18000, min: 10, max: 10000, time: '데이터 부족', description: '실시간 라이브 스트리밍 시청 서비스' },
      { id: 397, name: '인스타그램 실시간 라이브 스트리밍 시청 [120분]', price: 24000, min: 10, max: 10000, time: '데이터 부족', description: '실시간 라이브 스트리밍 시청 서비스' },
      { id: 398, name: '인스타그램 실시간 라이브 스트리밍 시청 [180분]', price: 36000, min: 10, max: 10000, time: '데이터 부족', description: '실시간 라이브 스트리밍 시청 서비스' },
      { id: 399, name: '인스타그램 실시간 라이브 스트리밍 시청 [240분]', price: 48000, min: 10, max: 10000, time: '데이터 부족', description: '실시간 라이브 스트리밍 시청 서비스' },
      { id: 400, name: '인스타그램 실시간 라이브 스트리밍 시청 [360분]', price: 72000, min: 10, max: 10000, time: '데이터 부족', description: '실시간 라이브 스트리밍 시청 서비스' },
      { id: 426, name: '인스타그램 실시간 라이브 스트리밍 시청 + 좋아요 + 댓글', price: 40000, min: 10, max: 10000, time: '데이터 부족', description: '실시간 라이브 스트리밍 시청 + 좋아요 + 댓글 서비스' }
    ],
    auto_likes_foreign: [
      { id: 105, name: '인스타그램 외국인 좋아요', price: 5000, min: 50, max: 10000, time: '데이터 부족', description: '외국인 좋아요 서비스' },
      { id: 116, name: '인스타그램 리얼 외국인 좋아요', price: 7000, min: 50, max: 10000, time: '데이터 부족', description: '리얼 외국인 좋아요 서비스' }
    ],
    auto_followers_foreign: [
      { id: 475, name: '인스타그램 외국인 팔로워', price: 10000, min: 100, max: 10000, time: '데이터 부족', description: '외국인 팔로워 서비스' }
    ],
    auto_comments_foreign: [
      { id: 480, name: '인스타그램 외국인 랜덤 댓글', price: 50000, min: 20, max: 1000, time: '데이터 부족', description: '외국인 랜덤 댓글 서비스' },
      { id: 481, name: '인스타그램 외국인 커스텀 댓글', price: 60000, min: 20, max: 1000, time: '데이터 부족', description: '외국인 커스텀 댓글 서비스' },
      { id: 358, name: '인스타그램 외국인 랜덤 이모지 댓글', price: 50000, min: 20, max: 1000, time: '데이터 부족', description: '외국인 랜덤 이모지 댓글 서비스' }
    ],
    auto_reels_views_foreign: [
      { id: 109, name: '인스타그램 동영상 조회수 [REEL/IGTV/VIDEO 가능]', price: 300, min: 100, max: 1000000, time: '데이터 부족', description: '동영상 조회수 서비스' },
      { id: 382, name: '인스타그램 동영상 조회수+저장+시간', price: 1200, min: 100, max: 1000000, time: '데이터 부족', description: '동영상 조회수+저장+시간 서비스' }
    ],
    auto_exposure_save_share_foreign: [
      { id: 142, name: '인스타그램 노출(+도달+추+프로필+기타)', price: 2500, min: 100, max: 1000000, time: '데이터 부족', description: '노출+도달+추+프로필+기타 서비스' },
      { id: 145, name: '인스타그램 노출(+도달+추+프로필+기타)', price: 5000, min: 100, max: 1000000, time: '데이터 부족', description: '노출+도달+추+프로필+기타 서비스' },
      { id: 312, name: '인스타그램 저장', price: 500, min: 10, max: 10000, time: '데이터 부족', description: '저장 서비스' },
      { id: 313, name: '인스타그램 공유', price: 8000, min: 10, max: 10000, time: '데이터 부족', description: '공유 서비스' }
    ],

    // 페이스북 세부 서비스 데이터
    facebook: {
      foreign_services: [
        { id: 154, name: '페이스북 외국인 페이지 좋아요+팔로워', price: 15000, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 156, name: '페이스북 외국인 페이지 팔로우', price: 15000, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 314, name: '페이스북 외국인 프로필 팔로우', price: 35000, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 318, name: '페이스북 외국인 게시물 좋아요', price: 10000, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 319, name: '페이스북 외국인 이모지 리액션 [LOVE]', price: 30000, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' }
      ],
      page_likes_korean: [
        { id: 226, name: 'KR 페이스북 리얼 한국인 페이지 좋아요+팔로워 [일반]', price: 250000, min: 20, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 227, name: 'KR 페이스북 리얼 한국인 페이지 좋아요+팔로워 [남성]', price: 400000, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 228, name: 'KR 페이스북 리얼 한국인 페이지 좋아요+팔로워 [여성]', price: 400000, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 229, name: 'KR 페이스북 리얼 한국인 페이지 좋아요+팔로워 [20대]', price: 400000, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 230, name: 'KR 페이스북 리얼 한국인 페이지 좋아요+팔로워 [30대]', price: 400000, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 231, name: 'KR 페이스북 리얼 한국인 페이지 좋아요+팔로워 [20대여자]', price: 500000, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 232, name: 'KR 페이스북 리얼 한국인 페이지 좋아요+팔로워 [20대남자]', price: 500000, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 233, name: 'KR 페이스북 리얼 한국인 페이지 좋아요+팔로워 [30대여자]', price: 500000, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 234, name: 'KR 페이스북 리얼 한국인 페이지 좋아요+팔로워 [30대남자]', price: 500000, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' }
      ],
      post_likes_korean: [
        { id: 198, name: 'KR 페이스북 리얼 한국인 게시물 좋아요 [일반]', price: 38000, min: 30, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 199, name: 'KR 페이스북 리얼 한국인 게시물 좋아요 [남성]', price: 55000, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 200, name: 'KR 페이스북 리얼 한국인 게시물 좋아요 [여성]', price: 55000, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 201, name: 'KR 페이스북 리얼 한국인 게시물 좋아요 [20대]', price: 55000, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 202, name: 'KR 페이스북 리얼 한국인 게시물 좋아요 [30대]', price: 55000, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 203, name: 'KR 페이스북 리얼 한국인 게시물 좋아요 [20대남자]', price: 60000, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 204, name: 'KR 페이스북 리얼 한국인 게시물 좋아요 [20대여자]', price: 60000, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 205, name: 'KR 페이스북 리얼 한국인 게시물 좋아요 [30대남자]', price: 60000, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 206, name: 'KR 페이스북 리얼 한국인 게시물 좋아요 [30대여자]', price: 60000, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' }
      ],
      post_comments_korean: [
        { id: 207, name: 'KR 페이스북 리얼 한국인 게시물 랜덤 댓글 [일반]', price: 270000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 209, name: 'KR 페이스북 리얼 한국인 게시물 랜덤 댓글 [남성]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 210, name: 'KR 페이스북 리얼 한국인 게시물 랜덤 댓글 [여성]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 211, name: 'KR 페이스북 리얼 한국인 게시물 랜덤 댓글 [20대]', price: 450000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 212, name: 'KR 페이스북 리얼 한국인 게시물 랜덤 댓글 [30대]', price: 450000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 213, name: 'KR 페이스북 리얼 한국인 게시물 랜덤 댓글 [20대여자]', price: 450000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 214, name: 'KR 페이스북 리얼 한국인 게시물 랜덤 댓글 [20대남자]', price: 450000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 215, name: 'KR 페이스북 리얼 한국인 게시물 랜덤 댓글 [30대여자]', price: 450000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 216, name: 'KR 페이스북 리얼 한국인 게시물 랜덤 댓글 [30대남자]', price: 450000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' }
      ],
      profile_follows_korean: [
        { id: 217, name: 'KR 페이스북 리얼 한국인 개인계정 팔로우 [일반]', price: 270000, min: 5, max: 500, time: '데이터 부족', description: '상세정보' },
        { id: 218, name: 'KR 페이스북 리얼 한국인 개인계정 팔로우 [남성]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 219, name: 'KR 페이스북 리얼 한국인 개인계정 팔로우 [여성]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 220, name: 'KR 페이스북 리얼 한국인 개인계정 팔로우 [20대]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 221, name: 'KR 페이스북 리얼 한국인 개인계정 팔로우 [30대]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 222, name: 'KR 페이스북 리얼 한국인 개인계정 팔로우 [20대여자]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 223, name: 'KR 페이스북 리얼 한국인 개인계정 팔로우 [20대남자]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 224, name: 'KR 페이스북 리얼 한국인 개인계정 팔로우 [30대여자]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 225, name: 'KR 페이스북 리얼 한국인 개인계정 팔로우 [30대남자]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' }
      ]
    },

    // 틱톡 세부 서비스 데이터
    tiktok: {
      likes_foreign: [
        { id: 458, name: '틱톡 외국인 리얼 좋아요', price: 9000, min: 100, max: 1000000, time: '10분', description: '상세정보' }
      ],
      views_foreign: [
        { id: 194, name: '틱톡 외국인 조회수', price: 400, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' }
      ],
      views_korean: [
        { id: 497, name: 'KR 틱톡 리얼 한국인 조회수 [15초]', price: 30000, min: 100, max: 30000, time: '데이터 부족', description: '상세정보' }
      ],
      followers_foreign: [
        { id: 476, name: '틱톡 외국인 리얼 계정 팔로워 [중속]', price: 25000, min: 100, max: 1000000, time: '7시간 12분', description: '상세정보' },
        { id: 478, name: '틱톡 외국인 리얼 계정 팔로워 [중고속]', price: 30000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' }
      ],
      save_share: [
        { id: 421, name: '틱톡 외국인 저장', price: 1500, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
        { id: 422, name: '틱톡 외국인 공유', price: 2000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' }
      ],
      live_streaming: [
        { id: 427, name: '틱톡 실시간 라이브 스트리밍 이모지 댓글', price: 8000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
        { id: 429, name: '틱톡 실시간 라이브 스트리밍 커스텀 댓글', price: 12000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
        { id: 430, name: '틱톡 실시간 라이브 스트리밍 100% 리얼 좋아요', price: 300000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' }
      ]
    },

    // 트위터 세부 서비스 데이터
    twitter: {
      followers_foreign: [
        { id: 197, name: '트위터(X) 외국인 팔로워', price: 80000, min: 100, max: 200000, time: '데이터 부족', description: '상세정보' }
      ]
    },

    // 카카오/네이버 세부 서비스 데이터
    kakao_naver: {
      kakao_services: [
        { id: 271, name: 'K사 카카오 채널 친구 추가', price: 300000, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' }
      ],
 
    },

    // 텔레그램 세부 서비스 데이터
    telegram: {
      subscribers: [
        { id: 437, name: '텔레그램 채널 구독자', price: 15000, min: 100, max: 50000, time: '데이터 부족', description: '상세정보' }
      ],
      views: [
        { id: 191, name: '텔레그램 게시물 조회수', price: 2000, min: 50, max: 10000, time: '데이터 부족', description: '상세정보' }
      ]
    },

    // 왓츠앱 세부 서비스 데이터
    whatsapp: {
      followers: [
        { id: 442, name: '왓츠앱 채널 팔로워', price: 30000, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' }
      ]
    },





    // 유튜브 세부 서비스 데이터
    youtube: {
      views: [
        { id: 360, name: 'KR 유튜브 리얼 한국인 조회수', price: 40000, min: 4000, max: 100000, time: '데이터 부족', description: '상세정보' },
        { id: 496, name: 'KR 유튜브 리얼 한국인 조회수 [20초 시청]', price: 70000, min: 10, max: 30000, time: '데이터 부족', description: '상세정보' },
        { id: 371, name: '유튜브 외국인 동영상 조회수', price: 6000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' }
      ],
      auto_views: [
        { id: 486, name: '🌐유튜브 외국인 동영상 자동 조회수', price: 6000, min: 1000, max: 10000000, time: '데이터 부족', description: '상세정보' }
      ],
      likes: [
        { id: 489, name: 'KR 유튜브 리얼 한국인 좋아요', price: 100000, min: 10, max: 1000, time: '데이터 부족', description: '상세정보' },
        { id: 136, name: '유튜브 외국인 좋아요', price: 8000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' }
      ],
      auto_likes: [
        { id: 487, name: '🌐유튜브 외국인 동영상 자동 좋아요', price: 8000, min: 20, max: 500000, time: '데이터 부족', description: '상세정보' }
      ],
      subscribers: [
        { id: 485, name: 'KR 유튜브 리얼 한국인 채널 구독자 [고속]', price: 400000, min: 50, max: 10000, time: '11시간 40분', description: '상세정보' },
        { id: 236, name: 'KR 유튜브 리얼 한국인 채널 구독자 [대량]', price: 700000, min: 200, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 500, name: '유튜브 외국인 채널 구독자', price: 65000, min: 100, max: 100000, time: '데이터 부족', description: '상세정보' }
      ],
      comments_shares: [
        { id: 482, name: 'KR 유튜브 한국인 동영상 AI 랜덤 댓글', price: 300000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 262, name: 'KR 유튜브 한국인 동영상 랜덤 댓글 [일반]', price: 390000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 263, name: 'KR 유튜브 한국인 동영상 랜덤 댓글 [남성]', price: 590000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 264, name: 'KR 유튜브 한국인 동영상 랜덤 댓글 [여성]', price: 590000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 265, name: 'KR 유튜브 한국인 동영상 랜덤 댓글 [20대]', price: 590000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 266, name: 'KR 유튜브 한국인 동영상 랜덤 댓글 [30대]', price: 590000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 267, name: 'KR 유튜브 한국인 동영상 랜덤 댓글 [20대 남성]', price: 700000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 268, name: 'KR 유튜브 한국인 동영상 랜덤 댓글 [20대 여성]', price: 700000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 269, name: 'KR 유튜브 한국인 동영상 랜덤 댓글 [30대 남성]', price: 700000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 270, name: 'KR 유튜브 한국인 동영상 랜덤 댓글 [30대 여성]', price: 700000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 261, name: 'KR 유튜브 한국 소셜 공유', price: 10000, min: 1, max: 1500, time: '데이터 부족', description: '상세정보' },
        { id: 423, name: '유튜브 외국인 랜덤 댓글', price: 50000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 138, name: '유튜브 외국인 커스텀 댓글', price: 60000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 260, name: '유튜브 외국인 이모지 랜덤 댓글', price: 50000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' }
      ],
      live_streaming: [
        { id: 393, name: '유튜브 외국인 실시간 라이브 스트리밍 [15분]', price: 10000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
        { id: 394, name: '유튜브 외국인 실시간 라이브 스트리밍 [30분]', price: 20000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
        { id: 395, name: '유튜브 외국인 실시간 라이브 스트리밍 [60분]', price: 40000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
        { id: 396, name: '유튜브 외국인 실시간 라이브 스트리밍 [90분]', price: 60000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
        { id: 397, name: '유튜브 외국인 실시간 라이브 스트리밍 [120분]', price: 80000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
        { id: 398, name: '유튜브 외국인 실시간 라이브 스트리밍 [180분]', price: 120000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' }
      ]
    },
    
    // 상위노출 패키지 서비스
    top_exposure: {
      manual: [
        // 🎯 추천탭 상위노출 (내계정) - 진입단계
      { id: 1003, name: '🎯 추천탭 상위노출 (내계정) - 진입단계 [4단계 패키지]', price: 20000000, min: 1, max: 1, time: '24-48시간', description: '진입단계 4단계 완전 패키지', package: true, steps: [
          { id: 122, name: '1단계: 실제 한국인 게시물 좋아요 [진입 단계]', quantity: 300, delay: 0, description: '🇰🇷 인스타그램 한국인 💎💎파워업 좋아요💖💖[💪인.게 최적화↑]' },
        { id: 329, name: '2단계: 파워 게시물 노출 + 도달 + 기타 유입', quantity: 10000, delay: 10, description: '5️⃣:[등록단계]파워게시물 노출 + 도달 + 홈 유입' },
        { id: 328, name: '3단계: 파워 게시물 저장 유입', quantity: 1000, delay: 10, description: '4️⃣[등록단계]파워 게시물 저장 유입' },
        { id: 342, name: '4단계: KR 인스타그램 리얼 한국인 랜덤 댓글', quantity: 5, delay: 10, description: '🇰🇷 인스타그램 리얼 한국인 랜덤 댓글💬' }
        ]},
        
        // 🎯 추천탭 상위노출 (내계정) - 유지단계
        { id: 1004, name: '🎯 추천탭 상위노출 (내계정) - 유지단계 [2단계 패키지]', price: 15000000, min: 1, max: 1, time: '30시간', description: '유지단계 2단계 완전 패키지 (90분 간격, 각 단계 10회 반복)', package: true, steps: [
          { id: 325, name: '1단계: 실제 한국인 게시물 좋아요 [90분당 100개씩 10회]', quantity: 100, delay: 90, repeat: 10, description: '[상승단계]:리얼 한국인 좋아요 - 90분 간격 10회 반복' },
          { id: 331, name: '2단계: 게시물 노출+도달+홈 [90분당 200개씩 10회]', quantity: 200, delay: 90, repeat: 10, description: '[유지단계]:게시물 노출+도달+홈 - 90분 간격 10회 반복' }
        ]},
        
        // 인스타 계정 상위노출 [30일] - Drip-feed 방식 사용 (runs: 30, interval: 1440)
        { id: 1005, name: '인스타 계정 상위노출 [30일]', price: 150000000, min: 1, max: 1, time: '30일', description: '인스타그램 프로필 방문 하루 400개씩 30일간', smmkings_id: 611, drip_feed: true, runs: 30, interval: 1440, drip_quantity: 400 },
        { id: 1001, name: '인스타 계정 상위노출 [30일]', price: 5000000, min: 1, max: 1, time: '30일', description: '인스타그램 계정 상위노출 서비스' },
        
        // 인스타 최적화 계정만들기 [30일]
        { id: 1002, name: '인스타 최적화 계정만들기 [30일]', price: 3000000, min: 1, max: 1, time: '30일', description: '인스타그램 최적화 계정 생성 서비스' }
      ]
    }
  }

//   platforms 데이터

  const platforms = [
    { id: 'recommended', name: '추천서비스', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/recommend.svg', color: '#f59e0b' },
    { id: 'event', name: '이벤트', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/brand.svg', color: '#8b5cf6' },
    { id: 'top-exposure', name: '상위노출', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/top.svg', color: '#f59e0b' },
    { id: 'instagram', name: '인스타그램', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/instagram.svg', color: '#e4405f' },
    { id: 'youtube', name: '유튜브', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/youtube.svg', color: '#ff0000' },
    { id: 'facebook', name: '페이스북', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/facebook.svg', color: '#1877f2' },
    { id: 'tiktok', name: '틱톡', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/tiktok.svg', color: '#000000' },
    { id: 'threads', name: '스레드', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/threads.svg', color: '#000000' },
    { id: 'twitter', name: '트위터', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/X.svg', color: '#1da1f2' },
    { id: 'kakao', name: '카카오', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/kakao.svg', color: '#fbbf24' },
    { id: 'telegram', name: '텔레그램', icon: '/TelegramLogo.svg.png', color: '#0088cc' },
    { id: 'whatsapp', name: '왓츠앱', icon: '/whatsapp-logo-new.svg', color: '#25d366' },
    // { id: 'news-media', name: '뉴스언론보도', icon: FileText, color: '#3b82f6' },
    // { id: 'experience-group', name: '체험단', icon: Users, color: '#10b981' },

    // { id: 'store-marketing', name: '스토어마케팅', icon: HomeIcon, color: '#f59e0b' },
    // { id: 'app-marketing', name: '어플마케팅', icon: Smartphone, color: '#3b82f6' },
    // { id: 'seo-traffic', name: 'SEO트래픽', icon: TrendingUp, color: '#8b5cf6' }
  ]

  export { instagramDetailedServices, platforms }