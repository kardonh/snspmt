// SMM KINGS API 서비스 매핑 유틸리티

// 플랫폼별 SMM KINGS 서비스 ID 매핑
export const SMMKINGS_SERVICE_MAPPING = {
  instagram: {
    followers_korean: {
      smmkings_id: 1, // 실제 SMM KINGS 서비스 ID로 변경 필요
      name: '팔로워 (한국인)',
      price: 120
    },
    followers_foreign: {
      smmkings_id: 2,
      name: '팔로워 (외국인)',
      price: 25
    },
    likes_korean: {
      smmkings_id: 3,
      name: '좋아요 (한국인)',
      price: 7
    },
    likes_foreign: {
      smmkings_id: 4,
      name: '좋아요 (외국인)',
      price: 1
    },
    comments_korean: {
      smmkings_id: 5,
      name: '댓글 (한국인)',
      price: 200
    },
    comments_foreign: {
      smmkings_id: 6,
      name: '댓글 (외국인)',
      price: 50
    },
    views_korean: {
      smmkings_id: 7,
      name: '조회수 (한국인)',
      price: 1
    },
    views_foreign: {
      smmkings_id: 8,
      name: '조회수 (외국인)',
      price: 0.5
    }
  },
  youtube: {
    followers_foreign: {
      smmkings_id: 101,
      name: '구독자 (외국인)',
      price: 50
    },
    followers_korean: {
      smmkings_id: 102,
      name: '구독자 (리얼 한국인)',
      price: 500
    },
    likes_foreign: {
      smmkings_id: 103,
      name: '좋아요 (외국인)',
      price: 7
    },
    comments_korean: {
      smmkings_id: 104,
      name: '댓글 (AI 랜덤 한국인)',
      price: 150
    },
    views_foreign: {
      smmkings_id: 105,
      name: '조회수 (외국인)',
      price: 7
    },
    views_korean: {
      smmkings_id: 106,
      name: '조회수 (리얼 한국인)',
      price: 25
    }
  },
  tiktok: {
    likes_foreign: {
      smmkings_id: 201,
      name: '좋아요 (외국인)',
      price: 6
    },
    followers_foreign: {
      smmkings_id: 202,
      name: '팔로워 (외국인)',
      price: 20
    },
    views_foreign: {
      smmkings_id: 203,
      name: '조회수 (외국인)',
      price: 2
    },
    comments_foreign: {
      smmkings_id: 204,
      name: '댓글 (외국인)',
      price: 200
    }
  },
  facebook: {
    followers_korean: {
      smmkings_id: 301,
      name: '개인계정 팔로우 (한국인)',
      price: 350
    },
    followers_foreign: {
      smmkings_id: 302,
      name: '프로필 팔로우 (외국인)',
      price: 20
    },
    likes_korean: {
      smmkings_id: 303,
      name: '게시물 좋아요 (리얼 한국인)',
      price: 50
    },
    likes_foreign: {
      smmkings_id: 304,
      name: '게시물 좋아요 (외국인)',
      price: 10
    },
    comments_korean: {
      smmkings_id: 305,
      name: '게시물 랜덤 댓글 (한국인)',
      price: 500
    }
  },
  twitter: {
    followers_real: {
      smmkings_id: 401,
      name: '팔로워 (리얼)',
      price: 50
    }
  },
  naver: {
    under_development: {
      smmkings_id: 0,
      name: '제작중',
      price: 0
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

// 플랫폼별 사용 가능한 서비스 목록 가져오기
export const getAvailableServices = (platform) => {
  const platformServices = SMMKINGS_SERVICE_MAPPING[platform]
  if (!platformServices) {
    return []
  }
  
  return Object.keys(platformServices).map(serviceId => ({
    id: serviceId,
    name: platformServices[serviceId].name,
    price: platformServices[serviceId].price,
    smmkings_id: platformServices[serviceId].smmkings_id
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
