import React, { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import './FAQPage.css'

const FAQPage = () => {
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [expandedItems, setExpandedItems] = useState({})

  const toggleExpanded = (id) => {
    setExpandedItems(prev => ({
      ...prev,
      [id]: !prev[id]
    }))
  }

  const categories = [
    { id: 'all', name: '전체' },
    { id: 'account', name: '회원가입 및 계정' },
    { id: 'service', name: '서비스 및 정책' },
    { id: 'order', name: '주문 및 진행' },
    { id: 'cancel-refund', name: '취소 및 환불' },
    { id: 'other', name: '기타' }
  ]

  const faqs = [
    // 회원가입 및 계정 관련
    {
      id: 1,
      category: 'account',
      question: '회원가입은 어떻게 하나요?',
      answer: '사이트 우측 상단의 \'회원가입\' 버튼을 통해 이메일 주소(ID)와 비밀번호를 설정하고, 이용약관에 동의하시면 간단하게 가입이 완료됩니다.'
    },
    {
      id: 2,
      category: 'account',
      question: '가입 시 실명을 사용해야 하나요?',
      answer: '아니요, 가입 시 실명을 요구하지는 않습니다. 하지만 타인의 명의를 도용하거나 허위 정보를 기재할 경우, 서비스 이용에 제한을 받거나 계약이 해지될 수 있습니다.'
    },
    {
      id: 3,
      category: 'account',
      question: '만 14세 미만도 가입할 수 있나요?',
      answer: '만 14세 미만 아동의 경우, 법정대리인(보호자)의 동의를 얻어야만 회원가입 및 서비스 이용이 가능합니다.'
    },
    {
      id: 4,
      category: 'account',
      question: '아이디(이메일)나 비밀번호를 잊어버렸어요.',
      answer: '로그인 페이지의 \'아이디/비밀번호 찾기\' 기능을 통해 가입 시 등록한 정보를 이용하여 찾으실 수 있습니다.'
    },
    {
      id: 5,
      category: 'account',
      question: '회원 정보를 변경하고 싶어요.',
      answer: '로그인 후 \'마이페이지\' 또는 \'개인정보관리\' 화면에서 언제든지 회원님의 개인정보를 직접 수정하실 수 있습니다.'
    },
    {
      id: 6,
      category: 'account',
      question: '회원 탈퇴는 어떻게 하며, 탈퇴하면 어떻게 되나요?',
      answer: '\'마이페이지\'에서 회원 탈퇴를 신청하시면 즉시 처리됩니다. 단, 탈퇴 시 사용하지 않은 충전금은 모두 소멸되며 복구되지 않으니 신중하게 결정해 주시기 바랍니다.'
    },
    {
      id: 7,
      category: 'account',
      question: '제 계정을 다른 사람에게 빌려주거나 판매해도 되나요?',
      answer: '아니요, 절대 불가합니다. 약관에 따라 회원 계정의 이용 권한을 타인에게 양도, 대여, 증여하거나 담보로 제공하는 행위는 엄격히 금지되어 있습니다. 적발 시 계정이 정지되거나 자격이 상실될 수 있습니다.'
    },
    
    // 서비스 및 정책 관련
    {
      id: 8,
      category: 'service',
      question: '소셜리티 서비스는 왜 이렇게 가격이 합리적인가요?',
      answer: '저희 소셜리티는 전 세계의 마케팅 주문을 대량으로 처리하여 트래픽 비용을 저렴하게 확보하고, 주문부터 처리까지의 전 과정을 자동화 시스템으로 구축하여 인건비를 크게 절감했습니다. 이를 통해 절감된 비용을 고객분들께 합리적인 가격으로 돌려드리고 있습니다.'
    },
    {
      id: 9,
      category: 'service',
      question: '제공되는 서비스는 제 SNS 계정에 안전한가요?',
      answer: '네, 안전합니다. 소셜리티는 유령 프로그램을 사용하는 방식이 아닌, 전 세계의 유효한 IP를 통한 실제 트래픽을 발생시키는 방식으로 서비스를 제공합니다.'
    },
    {
      id: 10,
      category: 'service',
      question: '팔로워나 좋아요는 실제 사용자인가요?',
      answer: '상품에 따라 다릅니다. 저희는 \'실제 유저\' 상품과 그렇지 않은 상품을 명확하게 구분하여 판매하고 있으니, 고객님의 마케팅 목적에 따라 원하시는 상품을 선택하여 구매하시면 됩니다.'
    },
    {
      id: 11,
      category: 'service',
      question: 'A/S(리필) 규정은 어떻게 되나요?',
      answer: '상품 설명에 \'A/S 보장\' 또는 \'리필\'이 명시된 경우에만 규정에 따라 제공됩니다. 단, 서비스 완료 후 계정 아이디를 변경하거나 링크를 삭제한 경우, 계정을 비공개로 전환한 경우, A/S 보장 기간 중 타사 서비스를 중복으로 이용한 경우, 소셜리티에서의 기존 주문 내역이 확인되지 않는 경우에는 A/S가 불가합니다.'
    },
    
    // 주문 및 진행 관련
    {
      id: 12,
      category: 'order',
      question: '서비스 주문은 어떻게 하나요?',
      answer: '로그인 후 원하시는 서비스를 선택하고, 정확한 SNS 게시물 링크 또는 아이디를 입력하여 주문하실 수 있습니다. 이후 충전금으로 결제가 완료되면 주문이 시스템에 자동으로 접수됩니다.'
    },
    {
      id: 13,
      category: 'order',
      question: '주문했는데 얼마나 기다려야 시작되나요?',
      answer: '서비스마다 차이가 있지만, 예를 들어 \'좋아요\' 서비스는 주문 후 평균 1분에서 60분 이내에 작업이 시작됩니다. 이는 평균 시작 시간으로, 서버 상황이나 인스타그램 로직 변동에 따라 지연될 수 있습니다. 48시간이 지나도 작업이 시작되지 않으면 고객센터로 문의해 주세요.'
    },
    {
      id: 14,
      category: 'order',
      question: '같은 링크에 중복해서 주문할 수 있나요?',
      answer: '네, 가능합니다. 단, 반드시 이전 주문의 상태가 \'완료\'로 변경된 것을 확인한 후 추가 주문을 하셔야 합니다. 이전 주문이 \'진행중\'인 상태에서 동일 링크에 추가 주문 시, 시스템 충돌로 수량 누락이 발생하며 이는 환불이나 보상 대상이 아닙니다.'
    },
    {
      id: 15,
      category: 'order',
      question: '주문 수량보다 적게 들어왔는데, 주문 상태는 \'완료\'로 표시돼요. 왜 그런가요?',
      answer: '가장 흔한 원인은 \'중복 주문\'입니다. 저희 시스템은 주문 시점의 \'시작 수량\'을 기준으로 \'목표 수량\'까지 작업을 진행합니다. 예를 들어 좋아요 10개가 있는 게시물에 100개를 주문하면, 시스템은 110개가 될 때까지 작업 후 \'완료\' 처리합니다. 만약 이 작업이 끝나기 전에 100개를 추가 주문하면, 두 번째 주문 역시 목표가 110개로 인식되어 먼저 끝난 주문과 함께 중복 처리됩니다.'
    },
    {
      id: 16,
      category: 'order',
      question: '소셜리티 서비스를 이용하면서 다른 곳의 서비스를 같이 이용해도 되나요?',
      answer: '아니요, 권장하지 않습니다. 작업이 중복 처리되어 정확한 수량 파악이 어렵고 누락이 발생할 수 있습니다. 이렇게 발생한 누락에 대해서는 추가 작업이나 환불이 불가능하니, 저희 서비스가 \'진행중\'일 때에는 타사 이용을 자제해 주십시오.'
    },
    {
      id: 17,
      category: 'order',
      question: '\'자동 좋아요\' 상품의 최소/최대 수량 설정은 무엇인가요?',
      answer: '새로 올리는 게시물에 좋아요가 너무 똑같은 수로 유입되는 것을 방지하기 위한 기능입니다. 예를 들어 최소 100, 최대 200으로 설정하면, 새 게시물이 올라올 때마다 100~200개 사이의 랜덤한 수량으로 좋아요가 자연스럽게 유입됩니다. 수량을 동일하게 설정하면(최소 100, 최대 100) 항상 100개씩 유입됩니다.'
    },
    {
      id: 18,
      category: 'order',
      question: '작업 속도를 조절할 수 있나요?',
      answer: '아쉽게도 개별 작업의 속도 조절은 불가능합니다. 다만, \'자동 좋아요\' 서비스의 경우 게시물을 올린 후 특정 시간(예: 30분 후)이 지나고 좋아요가 유입되도록 \'지연 설정\' 기능을 이용하실 수 있습니다.'
    },
    
    // 취소 및 환불 관련
    {
      id: 19,
      category: 'cancel-refund',
      question: '주문 취소가 가능한가요?',
      answer: '주문 정보는 시스템으로 자동 전송되어 즉시 처리를 시작합니다. 따라서 원칙적으로 주문 취소는 불가능합니다. 단, 시스템 오류로 작업 진행이 불가능하다고 판단될 경우, 정상 주문임에도 48시간 이상 작업이 시작되지 않아 고객센터에 취소 요청을 한 경우에는 시스템이 자동으로 주문을 취소하고 환불 처리합니다.'
    },
    {
      id: 20,
      category: 'cancel-refund',
      question: '주문이 취소/실패되면 환불은 어떻게 받나요?',
      answer: '주문이 시스템에 의해 취소되거나, \'부분 실패\'로 처리될 경우, 실패한 수량만큼의 금액이 즉시 사용자의 \'충전금\'으로 자동 환불됩니다. 환불된 내역은 \'주문내역\'에서 사용 금액이 0원으로 표시된 것을 통해 확인하실 수 있습니다.'
    },
    {
      id: 21,
      category: 'cancel-refund',
      question: '충전금을 현금으로 환불받고 싶어요.',
      answer: '네, 가능합니다. 카카오톡 1:1 문의로 신청해주시면 1~5 영업일 내에 처리해 드립니다. 무통장 입금 충전 건은 입금자명과 환불받을 계좌의 예금주명이 반드시 일치해야 합니다. 카드 결제 충전 건은 카드 결제는 승인 취소로 환불이 진행됩니다.'
    },
    
    // 기타
    {
      id: 22,
      category: 'other',
      question: '충전은 어떻게 하나요?',
      answer: '사이트 내 \'잔액충전\' 메뉴에서 충전이 가능하며, \'무통장입금\'과 \'카드결제\' 방식을 지원합니다. 자세한 내용은 \'잔액충전\' 메뉴의 설명을 참고해 주세요.'
    },
    {
      id: 23,
      category: 'other',
      question: '모바일 이용이 가능한가요?',
      answer: '네, 가능합니다. 저희 사이트는 모바일에 최적화되어 있어, 스마트폰 인터넷 브라우저 주소창에 주소를 입력하시면 언제 어디서든 PC처럼 편리하게 이용하실 수 있습니다.'
    },
    {
      id: 24,
      category: 'other',
      question: '고객센터 운영시간은 어떻게 되나요?',
      answer: '평일 오전 9시부터 오후 9시까지 운영하며, 점심시간은 11시 40분부터 13시까지입니다. 공휴일은 휴무입니다. 모든 문의는 카카오톡 1:1 상담 채널을 통해 24시간 내 답변을 원칙으로 합니다.'
    }
  ]

  const filteredFAQs = selectedCategory === 'all' 
    ? faqs 
    : faqs.filter(faq => faq.category === selectedCategory)

  // 디버깅: FAQ 데이터 확인
  console.log('FAQ 데이터:', faqs.length, '개')
  console.log('필터링된 FAQ:', filteredFAQs.length, '개')
  console.log('선택된 카테고리:', selectedCategory)

  return (
    <div className="faq-page">
      <div className="faq-container">
        <div className="faq-header">
          <h1>자주 묻는 질문</h1>
          <p>소셜리티를 이용하시면서 궁금한 점들을 쉽고 빠르게 해결하실 수 있도록 자주 묻는 질문들을 모았습니다.</p>
        </div>

        <div className="faq-categories">
          {categories.map(category => (
            <button
              key={category.id}
              className={`category-btn ${selectedCategory === category.id ? 'active' : ''}`}
              onClick={() => setSelectedCategory(category.id)}
            >
              {category.name}
            </button>
          ))}
        </div>

        <div className="faq-list">
          {filteredFAQs.map(faq => (
            <div key={faq.id} className="faq-item">
              <button
                className="faq-question"
                onClick={() => toggleExpanded(faq.id)}
              >
                <span>{faq.question}</span>
                {expandedItems[faq.id] ? (
                  <ChevronUp size={20} />
                ) : (
                  <ChevronDown size={20} />
                )}
              </button>
              <div className={`faq-answer ${expandedItems[faq.id] ? 'active' : ''}`}>
                <p>{faq.answer}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default FAQPage