// SMM KINGS API 서비스 매핑 유틸리티

// 플랫폼별 SMM KINGS 서비스 ID 매핑 (실제 SMM KINGS API 기반)
export const SMMKINGS_SERVICE_MAPPING = {
  instagram: {
    // 팔로워 서비스
    followers_hq_mixed_2m: {
      smmkings_id: 4972,
      name: '팔로워 [HQ 혼합 - 최대 250만]',
      price: 5.90, // 4.37달러 * 1350원
      min: 10,
      max: 2500000
    },
    followers_mixed_500k: {
      smmkings_id: 4973,
      name: '팔로워 [혼합 - 최대 50만]',
      price: 4.46, // 3.30달러 * 1350원
      min: 10,
      max: 500000
    },
    followers_real_active_500k: {
      smmkings_id: 3777,
      name: '팔로워 [실제 활동 - 최대 50만]',
      price: 3.59, // 2.66달러 * 1350원
      min: 50,
      max: 500000
    },
    followers_mixed_50k: {
      smmkings_id: 5607,
      name: '팔로워 [혼합 - 최대 5만]',
      price: 4.73, // 3.50달러 * 1350원
      min: 500,
      max: 50000
    },
    followers_hq_mixed_1m: {
      smmkings_id: 6362,
      name: '팔로워 [HQ 혼합 - 최대 100만]',
      price: 5.40, // 4.00달러 * 1350원
      min: 25,
      max: 1000000
    },
    
    // 좋아요 서비스
    likes_real_50k: {
      smmkings_id: 2683,
      name: '좋아요 [실제 - 최대 5만] [드랍 없음]',
      price: 0.53, // 0.39달러 * 1350원
      min: 50,
      max: 50000
    },
    likes_hq_500k: {
      smmkings_id: 4359,
      name: '좋아요 + 노출 + 도달 [HQ - 최대 50만]',
      price: 0.78, // 0.58달러 * 1350원
      min: 10,
      max: 500000
    },
    likes_real_100k: {
      smmkings_id: 3708,
      name: '좋아요 [실제 - 최대 10만] [삭제 불가]',
      price: 0.68, // 0.50달러 * 1350원
      min: 10,
      max: 100000
    },
    likes_real_300k: {
      smmkings_id: 2802,
      name: '좋아요 [실제 - 최대 30만] [드롭 없음]',
      price: 1.78, // 1.32달러 * 1350원
      min: 50,
      max: 300000
    },
    likes_real_exposure_300k: {
      smmkings_id: 3772,
      name: '좋아요 + 노출 [실제 - 최대 30만]',
      price: 0.77, // 0.57달러 * 1350원
      min: 10,
      max: 300000
    },
    
    // 한국인 좋아요 서비스
    likes_korean_uhq_20k: {
      smmkings_id: 2998,
      name: '좋아요 + 노출 + 도달 [한국 - UHQ] [삭제 불가]',
      price: 13.50, // 10.00달러 * 1350원
      min: 10,
      max: 20000
    },
    likes_korean_popular: {
      smmkings_id: 5009,
      name: '상위노출 - 한국 인기 게시물 좋아요',
      price: 11.34, // 8.40달러 * 1350원
      min: 100,
      max: 10000
    },
    likes_korean_uhq_10k: {
      smmkings_id: 5300,
      name: '좋아요 + 노출 [한국 - UHQ] [NON DROP]',
      price: 3.86, // 2.86달러 * 1350원
      min: 1,
      max: 10000
    },
    likes_korean_real_15k: {
      smmkings_id: 5164,
      name: '좋아요 + 노출 [한국 - 실제 & 활동] [시즌 3]',
      price: 9.11, // 6.75달러 * 1350원
      min: 20,
      max: 15000
    },
    likes_korean_real_10k: {
      smmkings_id: 2859,
      name: '좋아요 + 노출 [한국 - 실제 & 활동]',
      price: 11.79, // 8.73달러 * 1350원
      min: 5,
      max: 10000
    },
    
    // 댓글 서비스
    comments_random_hq_100: {
      smmkings_id: 5969,
      name: '랜덤 댓글 [HQ - AI 생성] [틈새/게시물 관련]',
      price: 12.15, // 9.00달러 * 1350원
      min: 5,
      max: 100
    },
    comments_random_mixed_1k: {
      smmkings_id: 3915,
      name: '랜덤 댓글 [혼합 - 최대 1천]',
      price: 9.72, // 7.20달러 * 1350원
      min: 2,
      max: 100
    },
    comments_custom_hq_3k: {
      smmkings_id: 3738,
      name: '커스텀 댓글 [HQ - 최대 3K]',
      price: 16.20, // 12.00달러 * 1350원
      min: 1,
      max: 100
    },
    comments_custom_hq_500: {
      smmkings_id: 5022,
      name: '커스텀 댓글 [HQ - 최대 500개]',
      price: 20.25, // 15.00달러 * 1350원
      min: 1,
      max: 1000
    },
    
    // 조회수 서비스
    views_posts_3m: {
      smmkings_id: 6274,
      name: '게시물 조회수',
      price: 0.020, // 0.015달러 * 1350원
      min: 10,
      max: 3000000
    },
    views_auto_posts_1m: {
      smmkings_id: 6275,
      name: '자동 게시물 조회수',
      price: 0.016, // 0.012달러 * 1350원
      min: 10,
      max: 1000000
    },
    views_video_global_100m: {
      smmkings_id: 5583,
      name: '비디오 조회수 [전 세계] [S6]',
      price: 0.012, // 0.009달러 * 1350원
      min: 100,
      max: 100000000
    },
    views_video_global_100m_s5: {
      smmkings_id: 5140,
      name: '비디오 조회수 [전 세계] [S5]',
      price: 0.016, // 0.012달러 * 1350원
      min: 100,
      max: 100000000
    },
    
    // 한국 조회수
    views_korea_2m: {
      smmkings_id: 5226,
      name: '한국 조회수',
      price: 0.068, // 0.05달러 * 1350원
      min: 500,
      max: 2000000
    },
    
    // 노출/도달 서비스
    exposure_reach_1m: {
      smmkings_id: 2869,
      name: '게시물 노출 + 도달 [S5] [즉각적]',
      price: 0.101, // 0.075달러 * 1350원
      min: 10,
      max: 1000000
    },
    exposure_reach_300k: {
      smmkings_id: 4306,
      name: '게시물 노출 + 도달 [S3] [즉각적]',
      price: 0.115, // 0.085달러 * 1350원
      min: 10,
      max: 300000
    },
    
    // 스토리 조회수
    story_views_hq_10k: {
      smmkings_id: 2879,
      name: '스토리 조회수 [HQ - 최대 1만] [모든 게시물]',
      price: 0.189, // 0.14달러 * 1350원
      min: 10,
      max: 10000
    },
    story_views_real_20k: {
      smmkings_id: 5296,
      name: '스토리 조회수 [실제 - 최대 2만] [마지막 게시물 5개]',
      price: 0.297, // 0.22달러 * 1350원
      min: 100,
      max: 10000
    },
    
    // 릴 좋아요
    reels_likes_s3_200k: {
      smmkings_id: 3797,
      name: '릴 좋아요 [S3]',
      price: 0.068, // 0.05달러 * 1350원
      min: 10,
      max: 200000
    },
    reels_likes_s2_300k: {
      smmkings_id: 3795,
      name: '릴 좋아요 [시즌2]',
      price: 0.162, // 0.12달러 * 1350원
      min: 10,
      max: 300000
    },
    
    // 공유/저장 서비스
    shares_high_speed_1m: {
      smmkings_id: 6290,
      name: '게시물/릴 공유 [시간당 2만 회 이상 고속 공유]',
      price: 0.020, // 0.015달러 * 1350원
      min: 10,
      max: 1000000
    },
    saves_real_4k: {
      smmkings_id: 3921,
      name: '게시물/릴 저장 [실제 - 최대 4K] [즉시]',
      price: 0.068, // 0.05달러 * 1350원
      min: 50,
      max: 4000
    },
    saves_real_30k: {
      smmkings_id: 767,
      name: '게시물/릴 저장 [실제 - 최대 3만] [즉시]',
      price: 0.095, // 0.07달러 * 1350원
      min: 10,
      max: 30000
    }
  },
  
  youtube: {
    // YouTube 구독자
    subscribers_5298: {
      smmkings_id: 5298,
      name: 'YouTube 구독자 [HQ - 최대 5만] [30일 리필]',
      price: 21.60,
      min: 10,
      max: 50000
    },
    subscribers_6337: {
      smmkings_id: 6337,
      name: 'YouTube 구독자 [HQ - 최대 20만] [30일 리필]',
      price: 37.80,
      min: 100,
      max: 200000
    },
    subscribers_4815: {
      smmkings_id: 4815,
      name: 'YouTube 구독자 [HQ - 최대 10만] [30일 리필]',
      price: 27.00,
      min: 100,
      max: 100000
    },
    subscribers_4116: {
      smmkings_id: 4116,
      name: 'YouTube 구독자 [HQ - 최대 50만] [30일 리필]',
      price: 11.10,
      min: 10,
      max: 500000
    },
    subscribers_4446: {
      smmkings_id: 4446,
      name: 'YouTube 구독자 [실제/HQ - 최대 25,000] [30일 리필]',
      price: 14.85,
      min: 10,
      max: 25000
    },
    subscribers_5288: {
      smmkings_id: 5288,
      name: 'YouTube 구독자 [혼합 - 최대 80만] [30일 리필]',
      price: 16.20,
      min: 10,
      max: 800000
    },
    subscribers_5746: {
      smmkings_id: 5746,
      name: 'YouTube 구독자 [혼합 - 최대 50만] [30일 리필]',
      price: 16.88,
      min: 10,
      max: 500000
    },
    subscribers_3825: {
      smmkings_id: 3825,
      name: 'YouTube 구독자 [HQ - 최대 10만] [14일 리필]',
      price: 35.10,
      min: 100,
      max: 100000
    },
    
    // YouTube 좋아요
    likes_1287: {
      smmkings_id: 1287,
      name: 'YouTube 좋아요 [실제 - 최대 1만]',
      price: 0.61,
      min: 10,
      max: 10000
    },
    likes_4020: {
      smmkings_id: 4020,
      name: 'YouTube 좋아요 [실제 - 최대 10만]',
      price: 0.92,
      min: 10,
      max: 100000
    },
    likes_2823: {
      smmkings_id: 2823,
      name: 'YouTube 좋아요 [HQ - 최대 50만]',
      price: 1.19,
      min: 10,
      max: 500000
    },
    likes_4443: {
      smmkings_id: 4443,
      name: 'YouTube 좋아요 [실제 - 최대 6만]',
      price: 1.46,
      min: 10,
      max: 60000
    },
    likes_2787: {
      smmkings_id: 2787,
      name: 'YouTube 좋아요 [HQ - 최대 4만] [평생 보장]',
      price: 2.16,
      min: 50,
      max: 40000
    },
    

    
    // YouTube 조회수
    views_6334: {
      smmkings_id: 6334,
      name: 'YouTube 조회수 [기본]',
      price: 3.59,
      min: 100,
      max: 200000
    },
    views_4091: {
      smmkings_id: 4091,
      name: 'YouTube 조회수 [수익 창출]',
      price: 9.72,
      min: 500,
      max: 200000
    },
    views_5952: {
      smmkings_id: 5952,
      name: 'YouTube 조회수 [유기적]',
      price: 2.63,
      min: 10000,
      max: 80000000
    }
  },
  
  tiktok: {
    // TikTok 조회수 서비스
    views_s9_1m: {
      smmkings_id: 3893,
      name: '조회수 [S9]',
      price: 0.020, // 0.015달러 * 1350원
      min: 100,
      max: 1000000
    },
    views_s8_5m: {
      smmkings_id: 3826,
      name: '조회수 [S8]',
      price: 0.024, // 0.018달러 * 1350원
      min: 100,
      max: 5000000
    },
    views_s2_50m: {
      smmkings_id: 2821,
      name: '조회수 [시즌2]',
      price: 0.031, // 0.023달러 * 1350원
      min: 100,
      max: 50000000
    },
    views_s4_50m: {
      smmkings_id: 3748,
      name: '조회수 [시즌4]',
      price: 0.014, // 0.01달러 * 1350원
      min: 100,
      max: 50000000
    },
    views_s10_5m: {
      smmkings_id: 3959,
      name: '조회수 [S10]',
      price: 0.014, // 0.01달러 * 1350원
      min: 100,
      max: 5000000
    },
    views_s6_80m: {
      smmkings_id: 3791,
      name: '조회수 [S6]',
      price: 0.019, // 0.014달러 * 1350원
      min: 100,
      max: 80000000
    },
    views_s7_10m: {
      smmkings_id: 3817,
      name: '조회수 [S7]',
      price: 0.008, // 0.006달러 * 1350원
      min: 100,
      max: 10000000
    },
    views_s5_10m: {
      smmkings_id: 3749,
      name: '조회수 [S5]',
      price: 0.008, // 0.006달러 * 1350원
      min: 100,
      max: 10000000
    },
    views_s1_1b: {
      smmkings_id: 2797,
      name: '조회수 [시즌 1] [즉시]',
      price: 0.054, // 0.04달러 * 1350원
      min: 100,
      max: 1000000000
    },
    views_desktop_1m: {
      smmkings_id: 5605,
      name: '조회수 [데스크톱 조회수 100%] [즉시]',
      price: 0.108, // 0.08달러 * 1350원
      min: 100,
      max: 1000000
    },
    views_mobile_1m: {
      smmkings_id: 5606,
      name: '조회수 [모바일 조회수 100%] [즉시]',
      price: 0.108, // 0.08달러 * 1350원
      min: 100,
      max: 1000000
    },
    views_s3_1m: {
      smmkings_id: 3719,
      name: '조회수 [시즌3] [즉시]',
      price: 0.162, // 0.12달러 * 1350원
      min: 500,
      max: 1000000
    },
    
    // TikTok 지역별 조회수
    views_us_5m: {
      smmkings_id: 4781,
      name: '조회수 [미국] [즉시]',
      price: 0.041, // 0.03달러 * 1350원
      min: 500,
      max: 5000000
    },
    views_korea_5m: {
      smmkings_id: 4778,
      name: '조회수 [대한민국] [즉시]',
      price: 0.041, // 0.03달러 * 1350원
      min: 500,
      max: 5000000
    },
    views_hk_5m: {
      smmkings_id: 5179,
      name: '조회수 [홍콩] [즉시]',
      price: 0.041, // 0.03달러 * 1350원
      min: 500,
      max: 5000000
    },
    views_japan_5m: {
      smmkings_id: 4779,
      name: '조회수 [일본] [즉시]',
      price: 0.041, // 0.03달러 * 1350원
      min: 500,
      max: 5000000
    },
    views_taiwan_5m: {
      smmkings_id: 4784,
      name: '조회수 [대만] [즉시]',
      price: 0.041, // 0.03달러 * 1350원
      min: 500,
      max: 5000000
    },
    views_turkey_5m: {
      smmkings_id: 4780,
      name: '조회수 [터키] [즉시]',
      price: 0.041, // 0.03달러 * 1350원
      min: 500,
      max: 5000000
    },
    views_brazil_5m: {
      smmkings_id: 4782,
      name: '조회수 [브라질] [즉시]',
      price: 0.041, // 0.03달러 * 1350원
      min: 500,
      max: 5000000
    },
    views_uk_5m: {
      smmkings_id: 4783,
      name: '조회수 [영국] [즉시]',
      price: 0.041, // 0.03달러 * 1350원
      min: 500,
      max: 5000000
    },
    views_indonesia_500m: {
      smmkings_id: 4785,
      name: '조회수 [인도네시아] [즉시]',
      price: 0.041, // 0.03달러 * 1350원
      min: 500,
      max: 500000000
    },
    views_albania_5m: {
      smmkings_id: 4934,
      name: '조회수 [알바니아] [즉시]',
      price: 0.041, // 0.03달러 * 1350원
      min: 500,
      max: 5000000
    },
    views_mexico_5m: {
      smmkings_id: 5672,
      name: '조회수 [멕시코] [즉시]',
      price: 0.041, // 0.03달러 * 1350원
      min: 500,
      max: 5000000
    },
    views_egypt_5m: {
      smmkings_id: 5180,
      name: '조회수 [이집트] [즉시]',
      price: 0.041, // 0.03달러 * 1350원
      min: 500,
      max: 5000000
    },
    
    // TikTok 좋아요 서비스
    likes_hq_1m: {
      smmkings_id: 3998,
      name: '좋아요 [HQ - 최대 100만]',
      price: 0.059, // 0.044달러 * 1350원
      min: 10,
      max: 1000000
    },
    likes_hq_3m: {
      smmkings_id: 2816,
      name: '좋아요 [HQ - 최대 300만] [30일 리필]',
      price: 0.093, // 0.069달러 * 1350원
      min: 10,
      max: 3000000
    },
    likes_hq_100k: {
      smmkings_id: 4008,
      name: '좋아요 [HQ - 최대 10만] [30일 리필]',
      price: 0.162, // 0.12달러 * 1350원
      min: 10,
      max: 100000
    },
    likes_real_100k: {
      smmkings_id: 3935,
      name: '좋아요 [실제 - 최대 10만] [365일 리필]',
      price: 0.169, // 0.125달러 * 1350원
      min: 10,
      max: 100000
    },
    likes_mixed_500k: {
      smmkings_id: 5064,
      name: '좋아요 [혼합 - 최대 50만]',
      price: 0.216, // 0.16달러 * 1350원
      min: 10,
      max: 500000
    },
    likes_hq_75k: {
      smmkings_id: 5060,
      name: '좋아요 [HQ - 최대 7만 5천] [30일 리필]',
      price: 0.392, // 0.29달러 * 1350원
      min: 10,
      max: 75000
    },
    likes_mixed_100k: {
      smmkings_id: 4203,
      name: '좋아요 [혼합 - 최대 10만]',
      price: 0.351, // 0.26달러 * 1350원
      min: 10,
      max: 100000
    },
    likes_views_hq_1m: {
      smmkings_id: 4818,
      name: '좋아요 + 조회수 [HQ] [30일 리필]',
      price: 0.405, // 0.30달러 * 1350원
      min: 10,
      max: 1000000
    },
    likes_us_50k: {
      smmkings_id: 5787,
      name: '좋아요 [미국 - 최대 50K] [NON DROP]',
      price: 3.713, // 2.75달러 * 1350원
      min: 10,
      max: 50000
    },
    likes_real_75k: {
      smmkings_id: 4204,
      name: '좋아요 [실제 - 최대 7만 5천] [40일 리필]',
      price: 4.725, // 3.50달러 * 1350원
      min: 10,
      max: 75000
    },
    likes_real_60k: {
      smmkings_id: 4003,
      name: '좋아요 [실제 - 최대 6만] [40일 리필]',
      price: 6.750, // 5.00달러 * 1350원
      min: 10,
      max: 60000
    },
    likes_real_100k_180d: {
      smmkings_id: 4009,
      name: '좋아요 [실제 - 최대 10만] [180일 리필]',
      price: 7.020, // 5.20달러 * 1350원
      min: 10,
      max: 100000
    },
    
    // TikTok 팔로워 서비스
    followers_hq_700k: {
      smmkings_id: 5750,
      name: '팔로워 [HQ - 최대 70만]',
      price: 2.188, // 1.621달러 * 1350원
      min: 10,
      max: 700000
    },
    followers_real_100k: {
      smmkings_id: 5186,
      name: '팔로워 [실제 - 최대 10만]',
      price: 5.670, // 4.20달러 * 1350원
      min: 10,
      max: 100000
    },
    followers_hq_3m: {
      smmkings_id: 3776,
      name: '팔로워 [HQ - 최대 3M] [365일 보증]',
      price: 15.525, // 11.50달러 * 1350원
      min: 50,
      max: 3000000
    },
    followers_real_100k_refill: {
      smmkings_id: 3934,
      name: '팔로워 [실제 - 최대 10만] [리필]',
      price: 12.764, // 9.455달러 * 1350원
      min: 10,
      max: 100000
    },
    followers_hq_mixed_100k: {
      smmkings_id: 4933,
      name: '팔로워 [HQ 혼합 - 최대 10만] [리필]',
      price: 11.813, // 8.75달러 * 1350원
      min: 100,
      max: 100000
    },
    followers_real_hq_200k: {
      smmkings_id: 3913,
      name: '팔로워 [실제/HQ - 최대 20만] [리필]',
      price: 8.108, // 6.006달러 * 1350원
      min: 5,
      max: 200000
    },
    followers_real_hq_2m: {
      smmkings_id: 3693,
      name: '팔로워 [실제/HQ - 최대 200만] [리필]',
      price: 10.631, // 7.875달러 * 1350원
      min: 10,
      max: 2000000
    },
    followers_real_500k: {
      smmkings_id: 3802,
      name: '팔로워 [실제 - 최대 50만] [리필]',
      price: 12.353, // 9.15달러 * 1350원
      min: 5,
      max: 500000
    },
    
    // TikTok 공유/저장 서비스
    shares_s3_100k: {
      smmkings_id: 5155,
      name: '공유 [S3]',
      price: 0.077, // 0.057달러 * 1350원
      min: 10,
      max: 100000
    },
    shares_s1_1m: {
      smmkings_id: 3789,
      name: '공유 [S1]',
      price: 0.389, // 0.288달러 * 1350원
      min: 50,
      max: 1000000
    },
    shares_real_10m: {
      smmkings_id: 2799,
      name: '공유 [실제]',
      price: 2.687, // 1.99달러 * 1350원
      min: 10,
      max: 10000000
    },
    saves_s1_100k: {
      smmkings_id: 4467,
      name: '비디오 저장 [S1]',
      price: 0.209, // 0.155달러 * 1350원
      min: 10,
      max: 100000
    },
    
    // TikTok 스토리 서비스
    story_likes_10k: {
      smmkings_id: 5010,
      name: '스토리 좋아요 [HQ - 최대 5천]',
      price: 0.203, // 0.15달러 * 1350원
      min: 50,
      max: 10000
    },
    
    // TikTok 댓글 서비스
    comments_random_20k: {
      smmkings_id: 4975,
      name: '랜덤 댓글 [혼합 - 최대 2만]',
      price: 3.375, // 2.50달러 * 1350원
      min: 1,
      max: 20000
    },
    comments_emoji_5k: {
      smmkings_id: 5200,
      name: '랜덤 이모티콘 댓글 [혼합 - 최대 5K]',
      price: 4.455, // 3.30달러 * 1350원
      min: 1,
      max: 5000
    },
    comments_real_5k: {
      smmkings_id: 3997,
      name: '랜덤 댓글 [실제 & 활동] [100% 진짜]',
      price: 19.440, // 14.40달러 * 1350원
      min: 5,
      max: 5000
    },
    comments_hq_10k: {
      smmkings_id: 4004,
      name: '랜덤 댓글 [HQ - 최대 10만]',
      price: 10.125, // 7.50달러 * 1350원
      min: 10,
      max: 10000
    },
    comments_custom_hq_20k: {
      smmkings_id: 4956,
      name: '커스텀 댓글 [HQ - 최대 20K]',
      price: 9.450, // 7.00달러 * 1350원
      min: 1,
      max: 20000
    },
    comments_custom_real_5k: {
      smmkings_id: 3987,
      name: '커스텀 댓글 [실제 - 최대 5K]',
      price: 12.656, // 9.375달러 * 1350원
      min: 10,
      max: 5000
    },
    comments_custom_real_50k: {
      smmkings_id: 5705,
      name: '커스텀 댓글 [실제 - 최대 5만]',
      price: 10.247, // 7.59달러 * 1350원
      min: 10,
      max: 50000
    },
    
    // TikTok 라이브 스트리밍 조회수
    live_views_15min: {
      smmkings_id: 4958,
      name: '라이브 스트리밍 조회수 [15분]',
      price: 1.823, // 1.35달러 * 1350원
      min: 100,
      max: 100000
    },
    live_views_30min: {
      smmkings_id: 4960,
      name: '라이브 스트리밍 조회수 [30분]',
      price: 3.645, // 2.70달러 * 1350원
      min: 100,
      max: 100000
    },
    live_views_60min: {
      smmkings_id: 4963,
      name: '라이브 스트리밍 조회수 [60분]',
      price: 7.290, // 5.40달러 * 1350원
      min: 100,
      max: 100000
    },
    live_views_90min: {
      smmkings_id: 4966,
      name: '라이브 스트리밍 조회수 [90분]',
      price: 10.935, // 8.10달러 * 1350원
      min: 100,
      max: 100000
    },
    live_views_120min: {
      smmkings_id: 5584,
      name: '라이브 스트리밍 조회수 [120분]',
      price: 14.580, // 10.80달러 * 1350원
      min: 100,
      max: 100000
    }
  },
  
  facebook: {
    // Facebook 팬페이지 좋아요
    page_likes_4052: {
      smmkings_id: 4052,
      name: '페이스북 팬페이지 좋아요 [HQ - 최대 8만]',
      price: 3.59,
      min: 100,
      max: 80000
    },
    page_likes_2734: {
      smmkings_id: 2734,
      name: '페이스북 팬페이지 좋아요 [실제/HQ - 최대 50만]',
      price: 2.83,
      min: 100,
      max: 500000
    },
    page_likes_2342: {
      smmkings_id: 2342,
      name: '페이스북 팬페이지 좋아요 [HQ - 최대 10만]',
      price: 8.78,
      min: 500,
      max: 100000
    },
    page_likes_2851: {
      smmkings_id: 2851,
      name: '페이스북 팬페이지 좋아요 [실제/HQ - 최대 150만]',
      price: 7.53,
      min: 100,
      max: 1500000
    },
    page_likes_2551: {
      smmkings_id: 2551,
      name: '페이스북 팬페이지 좋아요 [실제 - 최대 5만]',
      price: 20.25,
      min: 100,
      max: 50000
    },
    
    // Facebook 게시물 좋아요
    post_likes_2439: {
      smmkings_id: 2439,
      name: '페이스북 게시물 좋아요 [HQ - 최대 2만]',
      price: 6.10,
      min: 50,
      max: 20000
    },
    post_likes_2393: {
      smmkings_id: 2393,
      name: '페이스북 게시물 좋아요 [실제 - 최대 1천]',
      price: 4.73,
      min: 100,
      max: 1000
    },
    post_likes_2440: {
      smmkings_id: 2440,
      name: '페이스북 게시물 좋아요 [실제 - 최대 1천]',
      price: 20.66,
      min: 20,
      max: 1000
    },
    post_likes_2485: {
      smmkings_id: 2485,
      name: '페이스북 게시물 좋아요 [HQ - 최대 5만]',
      price: 10.94,
      min: 50,
      max: 100000
    },
    
    // Facebook 비디오 조회수
    video_views_2687: {
      smmkings_id: 2687,
      name: '페이스북 비디오 조회수 [실제 - 최대 10M]',
      price: 0.134,
      min: 500,
      max: 100000000
    },
    video_views_804: {
      smmkings_id: 804,
      name: '페이스북 비디오 조회수 [실제 - 최대 10M] [낮은 유지율]',
      price: 1.62,
      min: 500,
      max: 10000000
    },
    video_views_2688: {
      smmkings_id: 2688,
      name: '페이스북 비디오 조회수 [실제 - 최대 50만] [높은 유지율]',
      price: 2.70,
      min: 500,
      max: 10000000
    },
    video_views_4177: {
      smmkings_id: 4177,
      name: '페이스북 비디오 조회수 [실제 - 최대 100만] [수익 창출 가능]',
      price: 8.20,
      min: 500,
      max: 10000000
    },
    
    // Facebook 댓글
    comments_3982: {
      smmkings_id: 3982,
      name: '페이스북 커스텀 댓글 [실제 - 최대 8K]',
      price: 18.90,
      min: 10,
      max: 8000
    },
    comments_5079: {
      smmkings_id: 5079,
      name: '페이스북 커스텀 댓글 [실제 - 최대 2만]',
      price: 21.60,
      min: 10,
      max: 20000
    },
    comments_5080: {
      smmkings_id: 5080,
      name: '페이스북 커스텀 댓글 [HQ - 최대 1K] [느린 전송]',
      price: 3.40,
      min: 10,
      max: 1000
    },
    comments_1275: {
      smmkings_id: 1275,
      name: '페이스북 랜덤 댓글 [실제 - 최대 5K]',
      price: 40.50,
      min: 1,
      max: 5000
    }
  },
  
  twitter: {
    // X (트위터) 좋아요 [일본]
    likes_jp_4794: {
      smmkings_id: 4794,
      name: 'X (트위터) HQ 좋아요 [일본]',
      price: 6.32,
      min: 20,
      max: 6000
    },
    
    // X (트위터) 팔로워
    followers_5298: {
      smmkings_id: 5298,
      name: 'X (트위터) 팔로워 [HQ - 최대 5만] [30일 리필]',
      price: 21.60,
      min: 10,
      max: 50000
    },
    followers_6337: {
      smmkings_id: 6337,
      name: 'X (트위터) 팔로워 [HQ - 최대 20만] [30일 리필]',
      price: 37.80,
      min: 100,
      max: 200000
    },
    followers_4815: {
      smmkings_id: 4815,
      name: 'X (트위터) 팔로워 [HQ - 최대 10만] [30일 리필]',
      price: 27.00,
      min: 100,
      max: 100000
    },
    followers_4116: {
      smmkings_id: 4116,
      name: 'X (트위터) 팔로워 [HQ - 최대 50만] [30일 리필]',
      price: 11.10,
      min: 10,
      max: 500000
    },
    followers_4446: {
      smmkings_id: 4446,
      name: 'X (트위터) 팔로워 [실제/HQ - 최대 25,000] [30일 리필]',
      price: 14.85,
      min: 10,
      max: 25000
    },
    followers_5288: {
      smmkings_id: 5288,
      name: 'X (트위터) 팔로워 [혼합 - 최대 80만] [30일 리필]',
      price: 16.20,
      min: 10,
      max: 800000
    },
    followers_5746: {
      smmkings_id: 5746,
      name: 'X (트위터) 팔로워 [혼합 - 최대 50만] [30일 리필]',
      price: 16.88,
      min: 10,
      max: 500000
    },
    followers_3825: {
      smmkings_id: 3825,
      name: 'X (트위터) 팔로워 [HQ - 최대 10만] [14일 리필]',
      price: 35.10,
      min: 100,
      max: 100000
    },
    
    // X (트위터) 좋아요
    likes_4439: {
      smmkings_id: 4439,
      name: '트위터 좋아요 [실제/HQ] [30일 리필]',
      price: 1.35,
      min: 10,
      max: 1000000
    },
    likes_5036: {
      smmkings_id: 5036,
      name: '트위터 좋아요 [HQ - 최대 1만]',
      price: 4.21,
      min: 10,
      max: 10000
    },
    likes_5037: {
      smmkings_id: 5037,
      name: '트위터 좋아요 [실제 & 활성 - 최대 5천]',
      price: 4.21,
      min: 10,
      max: 4000
    },
    likes_kr_4796: {
      smmkings_id: 4796,
      name: '트위터 좋아요 [대한민국]',
      price: 6.32,
      min: 20,
      max: 500
    },
    
    // X (트위터) 리포스트
    reposts_5205: {
      smmkings_id: 5205,
      name: 'X (트위터) 리포스트 [실제 - 전 세계]',
      price: 2.03,
      min: 10,
      max: 50000
    },
    reposts_5671: {
      smmkings_id: 5671,
      name: 'X (트위터) 리포스트 [혼합 - 전 세계]',
      price: 21.52,
      min: 100,
      max: 500000
    },
    reposts_jp_4803: {
      smmkings_id: 4803,
      name: 'X (트위터) 리포스트 [일본]',
      price: 6.32,
      min: 10,
      max: 1000
    },
    reposts_id_4805: {
      smmkings_id: 4805,
      name: '트위터 리트윗 [인도네시아]',
      price: 0.33,
      min: 50,
      max: 50000
    },
    reposts_cn_4802: {
      smmkings_id: 4802,
      name: 'X (트위터) 리포스트 [중국]',
      price: 1.10,
      min: 50,
      max: 10000000
    },
    
    // X (트위터) POST 조회수/참여
    views_5193: {
      smmkings_id: 5193,
      name: 'X (트위터) 게시물 조회수 [S4]',
      price: 0.020,
      min: 100,
      max: 50000000
    },
    views_5102: {
      smmkings_id: 5102,
      name: 'X (트위터) 게시물 조회수 [S3]',
      price: 0.022,
      min: 500,
      max: 1000000000
    },
    views_4930: {
      smmkings_id: 4930,
      name: 'X (트위터) 게시물 조회수 [S2]',
      price: 0.027,
      min: 100,
      max: 200000000
    },
    views_4928: {
      smmkings_id: 4928,
      name: 'X (트위터) 게시물 조회수 [S1]',
      price: 0.027,
      min: 100,
      max: 10000000
    },
    views_5681: {
      smmkings_id: 5681,
      name: 'X (트위터) 게시물 조회수 [S5]',
      price: 0.063,
      min: 500,
      max: 1000000000
    },
    views_5726: {
      smmkings_id: 5726,
      name: 'X (트위터) 게시물 조회수 + 노출수 + 프로필 클릭수',
      price: 0.101,
      min: 100,
      max: 20000000
    },
    views_5679: {
      smmkings_id: 5679,
      name: 'X (트위터) 게시물 조회수 + 노출수 [초즉각적]',
      price: 0.513,
      min: 500,
      max: 10000000
    },
    views_us_6188: {
      smmkings_id: 6188,
      name: 'X (트위터) 게시물 조회수 + 노출수 [미국] [초즉각적]',
      price: 0.770,
      min: 500,
      max: 8000000
    },
    views_kr_6189: {
      smmkings_id: 6189,
      name: 'X (트위터) 게시물 조회수 + 노출수 [대한민국] [초즉각적]',
      price: 0.770,
      min: 500,
      max: 1000000
    },
    views_jp_6190: {
      smmkings_id: 6190,
      name: 'X (트위터) 게시물 조회수 + 노출수 [일본] [초즉각]',
      price: 0.770,
      min: 500,
      max: 500000
    },
    views_tr_6191: {
      smmkings_id: 6191,
      name: 'X (트위터) 게시물 조회수 + 노출수 [터키] [초즉각적]',
      price: 0.770,
      min: 500,
      max: 2000000
    },
    views_nl_6192: {
      smmkings_id: 6192,
      name: 'X (트위터) 게시물 조회수 + 노출수 [네덜란드] [초즉각적]',
      price: 0.648,
      min: 500,
      max: 5000000
    },
    
    // 지역별 조회수
    views_us_4929: {
      smmkings_id: 4929,
      name: 'X (트위터) 게시물 조회수 [미국]',
      price: 0.108,
      min: 500,
      max: 100000000
    },
    views_uk_4942: {
      smmkings_id: 4942,
      name: 'X (트위터) 게시물 조회수 [영국]',
      price: 0.108,
      min: 500,
      max: 10000000
    },
    views_kr_4939: {
      smmkings_id: 4939,
      name: 'X (트위터) 게시물 조회수 [대한민국]',
      price: 0.108,
      min: 500,
      max: 10000000
    },
    views_jp_4940: {
      smmkings_id: 4940,
      name: 'X (트위터) 게시물 조회수 [일본]',
      price: 0.108,
      min: 500,
      max: 10000000
    },
    views_hk_4944: {
      smmkings_id: 4944,
      name: 'X (트위터) 게시물 조회수 [홍콩]',
      price: 0.108,
      min: 500,
      max: 10000000
    },
    views_in_4946: {
      smmkings_id: 4946,
      name: 'X (트위터) 게시물 조회수 [인도]',
      price: 0.108,
      min: 500,
      max: 10000000
    },
    views_id_4941: {
      smmkings_id: 4941,
      name: 'X (트위터) 게시물 조회수 [인도네시아]',
      price: 0.108,
      min: 500,
      max: 10000000
    },
    views_de_4943: {
      smmkings_id: 4943,
      name: 'X (트위터) 게시물 조회수 [독일]',
      price: 0.108,
      min: 500,
      max: 10000000
    },
    views_br_4945: {
      smmkings_id: 4945,
      name: 'X (트위터) 게시물 조회수 [브라질]',
      price: 0.108,
      min: 500,
      max: 1000000
    },
    
    // X (트위터) 비디오 조회수/참여
    video_views_5206: {
      smmkings_id: 5206,
      name: 'X (트위터) 비디오 조회수 + 노출수 [즉시] [안정적]',
      price: 0.432,
      min: 500,
      max: 10000000
    },
    video_views_4927: {
      smmkings_id: 4927,
      name: 'X (트위터) 영상 조회수',
      price: 0.108,
      min: 500,
      max: 50000000
    },
    video_views_3722: {
      smmkings_id: 3722,
      name: 'X (트위터) 영상 조회수 + 노출수 [S1]',
      price: 0.068,
      min: 100,
      max: 500000
    },
    video_views_us_4906: {
      smmkings_id: 4906,
      name: 'X (트위터) 비디오 조회수 + 노출수 [미국]',
      price: 0.122,
      min: 500,
      max: 800000
    },
    video_views_kr_4907: {
      smmkings_id: 4907,
      name: 'X (트위터) 영상 조회수 + 노출수 [대한민국]',
      price: 0.122,
      min: 500,
      max: 250000
    },
    video_views_hk_5292: {
      smmkings_id: 5292,
      name: 'X (트위터) 영상 조회수 + 노출수 [홍콩]',
      price: 0.122,
      min: 500,
      max: 500000
    },
    video_views_jp_5293: {
      smmkings_id: 5293,
      name: 'X (트위터) 영상 조회수 + 노출수 [일본]',
      price: 0.122,
      min: 500,
      max: 500000
    },
    video_views_id_4908: {
      smmkings_id: 4908,
      name: 'X (트위터) 비디오 조회수 + 노출수 [인도네시아]',
      price: 0.122,
      min: 500,
      max: 250000
    },
    video_views_uk_4909: {
      smmkings_id: 4909,
      name: 'X (트위터) 비디오 조회수 + 노출수 [영국]',
      price: 0.122,
      min: 500,
      max: 250000
    },
    video_views_tr_4910: {
      smmkings_id: 4910,
      name: 'X (트위터) 비디오 조회수 + 노출수 [터키]',
      price: 0.122,
      min: 500,
      max: 250000
    },
    video_views_ae_4911: {
      smmkings_id: 4911,
      name: 'X (트위터) 비디오 조회수 + 노출수 [UAE]',
      price: 0.122,
      min: 500,
      max: 250000
    },
    video_views_it_4912: {
      smmkings_id: 4912,
      name: 'X (트위터) 비디오 조회수 + 노출수 [이탈리아]',
      price: 0.122,
      min: 500,
      max: 250000
    },
    video_views_in_4913: {
      smmkings_id: 4913,
      name: 'X (트위터) 비디오 조회수 + 노출수 [인도]',
      price: 0.122,
      min: 500,
      max: 10000000
    },
    
    // X (트위터) 노출/참여
    exposure_5190: {
      smmkings_id: 5190,
      name: 'X (트위터) 북마크 게시 [시즌2] [즉시]',
      price: 1.46,
      min: 20,
      max: 5000
    },
    exposure_5730: {
      smmkings_id: 5730,
      name: 'X (트위터) 게시물 노출 + 프로필 방문 + 참여',
      price: 0.043,
      min: 100,
      max: 50000000
    },
    
    // X (트위터) 우주 청취자
    space_5210: {
      smmkings_id: 5210,
      name: '트위터 스페이스 청취자 [5분]',
      price: 0.405,
      min: 10,
      max: 100000
    },
    space_5211: {
      smmkings_id: 5211,
      name: '트위터 스페이스 청취자 [15분]',
      price: 0.810,
      min: 10,
      max: 100000
    },
    space_5213: {
      smmkings_id: 5213,
      name: '트위터 스페이스 청취자 [45분]',
      price: 2.16,
      min: 10,
      max: 100000
    },
    space_5214: {
      smmkings_id: 5214,
      name: '트위터 스페이스 리스너 [60분]',
      price: 2.70,
      min: 10,
      max: 100000
    },
    space_5215: {
      smmkings_id: 5215,
      name: '트위터 스페이스 리스너스 [90분]',
      price: 4.05,
      min: 10,
      max: 100000
    },
    space_5216: {
      smmkings_id: 5216,
      name: '트위터 스페이스 리스너 [120분]',
      price: 5.67,
      min: 10,
      max: 100000
    }
  },
  
  naver: {
    // 네이버 라이브
    live_5978: {
      smmkings_id: 5978,
      name: '네이버 라이브 [데스크톱] [대한민국]',
      price: 0.85,
      min: 500,
      max: 2000000
    },
    live_6306: {
      smmkings_id: 6306,
      name: '네이버 라이브 [모바일 iOS] [대한민국]',
      price: 1.23,
      min: 500,
      max: 1000000
    }
  },
  
  threads: {
    // 🇰🇷 스레드 [대한민국]
    likes_kr_5689: {
      smmkings_id: 5689,
      name: '스레드 좋아요 [대한민국] [실제]',
      price: 10.53,
      min: 5,
      max: 10000
    },
    auto_likes_kr_5704: {
      smmkings_id: 5704,
      name: 'AUTO 좋아요 스레드 [대한민국]',
      price: 10.53,
      min: 5,
      max: 10000
    },
    followers_kr_5690: {
      smmkings_id: 5690,
      name: '스레드 팔로워 [대한민국] [실제]',
      price: 48.60,
      min: 5,
      max: 10000
    },
    
    // 🇯🇵 스레드 [일본]
    likes_jp_5687: {
      smmkings_id: 5687,
      name: '스레드 좋아요 [일본] [실제]',
      price: 10.53,
      min: 5,
      max: 10000
    },
    auto_likes_jp_5703: {
      smmkings_id: 5703,
      name: '스레드 AUTO 좋아요 [일본]',
      price: 10.53,
      min: 5,
      max: 10000
    },
    followers_jp_5688: {
      smmkings_id: 5688,
      name: '스레드 팔로워 [일본] [실제]',
      price: 48.60,
      min: 5,
      max: 40000
    }
  }
}

// SMM KINGS 서비스 ID로 매핑된 서비스 정보 가져오기
export const getSMMKingsServiceInfo = (platform, serviceId) => {
  const platformServices = SMMKINGS_SERVICE_MAPPING[platform]
  if (!platformServices) {
    return null
  }
  
  return platformServices[serviceId] || null
}

// SMM KINGS 서비스 ID 가져오기
export const getSMMKingsServiceId = (platform, serviceId) => {
  const serviceInfo = getSMMKingsServiceInfo(platform, serviceId)
  return serviceInfo ? serviceInfo.smmkings_id : null
}

// SMM KINGS 서비스 가격 가져오기
export const getSMMKingsServicePrice = (platform, serviceId) => {
  const serviceInfo = getSMMKingsServiceInfo(platform, serviceId)
  return serviceInfo ? serviceInfo.price : 0
}

// SMM KINGS 서비스 이름 가져오기
export const getSMMKingsServiceName = (platform, serviceId) => {
  const serviceInfo = getSMMKingsServiceInfo(platform, serviceId)
  return serviceInfo ? serviceInfo.name : serviceId
}

// SMM KINGS 서비스 최소 수량 가져오기
export const getSMMKingsServiceMin = (platform, serviceId) => {
  const serviceInfo = getSMMKingsServiceInfo(platform, serviceId)
  return serviceInfo ? serviceInfo.min : 0
}

// SMM KINGS 서비스 최대 수량 가져오기
export const getSMMKingsServiceMax = (platform, serviceId) => {
  const serviceInfo = getSMMKingsServiceInfo(platform, serviceId)
  return serviceInfo ? serviceInfo.max : 0
}

// 플랫폼별 사용 가능한 서비스 목록 가져오기
export const getAvailableServices = (platform) => {
  if (platform === 'recommended') {
    // 추천서비스는 여러 플랫폼의 인기 서비스들을 합침
    const recommendedServices = []
    
    // Instagram 인기 서비스들
    const instagramServices = SMMKINGS_SERVICE_MAPPING.instagram
    if (instagramServices) {
      Object.keys(instagramServices).forEach(serviceId => {
        if (serviceId.includes('followers') || serviceId.includes('likes') || serviceId.includes('popular')) {
          recommendedServices.push({
            id: serviceId,
            name: instagramServices[serviceId].name,
            price: instagramServices[serviceId].price,
            smmkings_id: instagramServices[serviceId].smmkings_id,
            min: instagramServices[serviceId].min,
            max: instagramServices[serviceId].max,
            platform: 'instagram'
          })
        }
      })
    }
    
    // YouTube 인기 서비스들
    const youtubeServices = SMMKINGS_SERVICE_MAPPING.youtube
    if (youtubeServices) {
      Object.keys(youtubeServices).forEach(serviceId => {
        if (serviceId.includes('subscribers') || serviceId.includes('views')) {
          recommendedServices.push({
            id: serviceId,
            name: youtubeServices[serviceId].name,
            price: youtubeServices[serviceId].price,
            smmkings_id: youtubeServices[serviceId].smmkings_id,
            min: youtubeServices[serviceId].min,
            max: youtubeServices[serviceId].max,
            platform: 'youtube'
          })
        }
      })
    }
    
    // TikTok 인기 서비스들
    const tiktokServices = SMMKINGS_SERVICE_MAPPING.tiktok
    if (tiktokServices) {
      Object.keys(tiktokServices).forEach(serviceId => {
        if (serviceId.includes('followers') || serviceId.includes('views')) {
          recommendedServices.push({
            id: serviceId,
            name: tiktokServices[serviceId].name,
            price: tiktokServices[serviceId].price,
            smmkings_id: tiktokServices[serviceId].smmkings_id,
            min: tiktokServices[serviceId].min,
            max: tiktokServices[serviceId].max,
            platform: 'tiktok'
          })
        }
      })
    }
    
    // Facebook 인기 서비스들
    const facebookServices = SMMKINGS_SERVICE_MAPPING.facebook
    if (facebookServices) {
      Object.keys(facebookServices).forEach(serviceId => {
        if (serviceId.includes('page_likes')) {
          recommendedServices.push({
            id: serviceId,
            name: facebookServices[serviceId].name,
            price: facebookServices[serviceId].price,
            smmkings_id: facebookServices[serviceId].smmkings_id,
            min: facebookServices[serviceId].min,
            max: facebookServices[serviceId].max,
            platform: 'facebook'
          })
        }
      })
    }
    
    // Twitter 인기 서비스들
    const twitterServices = SMMKINGS_SERVICE_MAPPING.twitter
    if (twitterServices) {
      Object.keys(twitterServices).forEach(serviceId => {
        if (serviceId.includes('followers')) {
          recommendedServices.push({
            id: serviceId,
            name: twitterServices[serviceId].name,
            price: twitterServices[serviceId].price,
            smmkings_id: twitterServices[serviceId].smmkings_id,
            min: twitterServices[serviceId].min,
            max: twitterServices[serviceId].max,
            platform: 'twitter'
          })
        }
      })
    }
    
    return recommendedServices
  }
  
  const platformServices = SMMKINGS_SERVICE_MAPPING[platform]
  if (!platformServices) {
    return []
  }
  
  return Object.keys(platformServices).map(serviceId => ({
    id: serviceId,
    name: platformServices[serviceId].name,
    price: platformServices[serviceId].price,
    smmkings_id: platformServices[serviceId].smmkings_id,
    min: platformServices[serviceId].min,
    max: platformServices[serviceId].max
  }))
}

// 실제 SMM KINGS API에서 서비스 목록을 가져와서 매핑 업데이트
export const updateServiceMappingFromAPI = async (apiServices) => {
  // 실제 SMM KINGS API 응답을 기반으로 매핑을 동적으로 업데이트
  // 이 함수는 API 응답 구조에 따라 구현해야 함
  console.log('API Services:', apiServices)
  
  // 예시: API 응답을 기반으로 매핑 업데이트
  if (apiServices && Array.isArray(apiServices)) {
    apiServices.forEach(service => {
      // 서비스 정보를 기반으로 매핑 업데이트 로직
      console.log(`Service ID: ${service.service}, Name: ${service.name}, Category: ${service.category}`)
    })
  }
}
