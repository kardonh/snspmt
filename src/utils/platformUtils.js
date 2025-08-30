export const getPlatformInfo = (platform) => {
  const platforms = {
    recommended: {
      name: '추천서비스',
      unitPrice: 20,
      services: ['instagram_followers', 'instagram_likes', 'instagram_popular', 'youtube_subscribers', 'youtube_views', 'tiktok_followers', 'tiktok_views', 'facebook_page_likes', 'twitter_followers']
    },
    instagram: {
      name: '인스타그램',
      unitPrice: 25,
      services: ['followers_korean', 'followers_foreign', 'likes_korean', 'likes_foreign', 'comments_korean', 'comments_foreign', 'views_korean', 'views_foreign']
    },
    youtube: {
      name: '유튜브',
      unitPrice: 30,
      services: ['followers_korean', 'likes_foreign', 'views_foreign']
    },
    tiktok: {
      name: '틱톡',
      unitPrice: 22,
      services: ['likes_foreign', 'followers_foreign', 'views_foreign', 'comments_foreign', 'shares_foreign', 'story_foreign', 'live_foreign']
    },
    threads: {
      name: '스레드',
      unitPrice: 25,
      services: ['followers_foreign', 'likes_foreign']
    },
    facebook: {
      name: '페이스북',
      unitPrice: 20,
      services: ['page_likes_foreign', 'post_likes_foreign', 'video_views_foreign', 'comments_foreign']
    },
    twitter: {
      name: '트위터',
      unitPrice: 28,
      services: ['followers_real']
    },
    naver: {
      name: '네이버',
      unitPrice: 15,
      services: ['live_foreign']
    }
  }
  
  return platforms[platform] || platforms.tiktok
}

export const calculatePrice = (service, quantity, platform) => {
  let basePrice = 0
  
  // Instagram 서비스별 단가 적용
  if (platform === 'instagram') {
    switch (service) {
      case 'followers_korean': // 한국인 팔로워: 120원
        basePrice = 120 * quantity
        break
      case 'followers_foreign': // 외국인 팔로워: 1원
        basePrice = 1 * quantity
        break
      case 'likes_korean': // 한국인 좋아요: 120원
        basePrice = 120 * quantity
        break
      case 'likes_foreign': // 외국인 좋아요: 1원
        basePrice = 1 * quantity
        break
      case 'comments_korean': // 한국인 랜덤 댓글: 200원
        basePrice = 200 * quantity
        break
      case 'comments_foreign': // 외국인 랜덤 댓글: 50원
        basePrice = 50 * quantity
        break
      case 'views_korean': // 한국인 조회수: 120원
        basePrice = 120 * quantity
        break
      case 'views_foreign': // 외국인 조회수: 1원
        basePrice = 1 * quantity
        break
      default:
        basePrice = getPlatformInfo(platform).unitPrice * quantity
    }
  } else if (platform === 'youtube') {
    // YouTube 서비스별 단가 적용
    switch (service) {
      case 'subscribers_foreign': // 외국인 구독자: 30원
        basePrice = 30 * quantity
        break
      case 'views_foreign': // 외국인 조회수: 30원
        basePrice = 30 * quantity
        break
      default:
        basePrice = getPlatformInfo(platform).unitPrice * quantity
    }
  } else if (platform === 'tiktok') {
    // TikTok 서비스별 단가 적용
    switch (service) {
      case 'likes_foreign': // 외국인 좋아요: 22원
        basePrice = 22 * quantity
        break
      case 'followers_foreign': // 외국인 계정 팔로워: 22원
        basePrice = 22 * quantity
        break
      case 'views_foreign': // 외국인 조회수: 22원
        basePrice = 22 * quantity
        break
      default:
        basePrice = getPlatformInfo(platform).unitPrice * quantity
    }
  } else if (platform === 'twitter') {
    // Twitter 서비스별 단가 적용
    switch (service) {
      case 'followers_real': // 리얼 팔로워: 50원
        basePrice = 50 * quantity
        break
      default:
        basePrice = getPlatformInfo(platform).unitPrice * quantity
    }
  } else if (platform === 'facebook') {
    // Facebook 서비스별 단가 적용
    switch (service) {
      case 'followers_korean': // 한국인 개인계정 팔로우: 350원
        basePrice = 350 * quantity
        break
      case 'followers_foreign': // 외국인 프로필 팔로우: 20원
        basePrice = 20 * quantity
        break
      case 'likes_korean': // 리얼 한국인 게시물 좋아요: 50원
        basePrice = 50 * quantity
        break
      case 'likes_foreign': // 외국인 게시물 좋아요: 10원
        basePrice = 10 * quantity
        break
      case 'comments_korean': // 한국인 게시물 랜덤 댓글: 500원
        basePrice = 500 * quantity
        break
      default:
        basePrice = getPlatformInfo(platform).unitPrice * quantity
    }
  } else if (platform === 'naver') {
    // 제작중인 서비스는 가격 0
    basePrice = 0
  } else {
    // 다른 플랫폼들은 기본 단가 사용
    basePrice = getPlatformInfo(platform).unitPrice * quantity
  }
  
  // 할인 적용
  let discount = 0
  if (quantity >= 5000) {
    discount = 20
  } else if (quantity >= 1000) {
    discount = 15
  } else if (quantity >= 500) {
    discount = 10
  }
  
  const finalPrice = basePrice * (1 - discount / 100)
  return Math.round(finalPrice)
}

export const getServiceName = (serviceId) => {
  const serviceNames = {
    followers_korean: '팔로워 (한국인)',
    followers_foreign: '팔로워 (외국인)',
    likes_korean: '좋아요 (한국인)',
    likes_foreign: '좋아요 (외국인)',
    comments_korean: '댓글 (한국인)',
    comments_foreign: '댓글 (외국인)',
    views_korean: '조회수 (한국인)',
    views_foreign: '조회수 (외국인)',
    views: '조회수',
    followers: '팔로워',
    likes: '좋아요',
    subscribers: '구독자',
    comments: '댓글',
    // YouTube 서비스명 추가
    followers_foreign: '구독자 (외국인)',
    followers_korean: '구독자 (리얼 한국인)',
    likes_foreign: '좋아요 (외국인)',
    comments_korean: '댓글 (AI 랜덤 한국인)',
    views_foreign: '조회수 (외국인)',
    views_korean: '조회수 (리얼 한국인)',
    // TikTok 서비스명 추가
    likes_foreign: '좋아요 (외국인)',
    followers_foreign: '팔로워 (외국인)',
    views_foreign: '조회수 (외국인)',
    comments_foreign: '댓글 (외국인)',
    // Twitter 서비스명 추가
    followers_real: '팔로워 (리얼)',
    // Facebook 서비스명 추가
    followers_korean: '개인계정 팔로우 (한국인)',
    followers_foreign: '프로필 팔로우 (외국인)',
    likes_korean: '게시물 좋아요 (리얼 한국인)',
    likes_foreign: '게시물 좋아요 (외국인)',
    comments_korean: '게시물 랜덤 댓글 (한국인)',
    page_likes: '페이지 좋아요',
    post_likes: '게시물 좋아요',
    retweets: '리트윗',
    channel_followers: '채널 팔로워',
    under_development: '제작중'
  }
  
  return serviceNames[serviceId] || serviceId
}
