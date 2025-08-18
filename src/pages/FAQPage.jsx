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
    { id: 'cancel-refund', name: '취소, 환불, AS' },
    { id: 'service', name: 'SNS샵 서비스' },
    { id: 'instagram', name: '인스타그램' }
  ]

  const faqs = [
    {
      id: 1,
      category: 'cancel-refund',
      question: '주문 취소 가능한가요?',
      answer: '주문 접수 후 30분 이내에는 취소가 가능합니다. 30분이 지난 후에는 작업이 시작되어 취소가 불가능합니다.'
    },
    {
      id: 2,
      category: 'cancel-refund',
      question: 'A/S 규정은 어떻게 되나요?',
      answer: '작업 완료 후 7일 이내에 문제가 발생한 경우 무료로 재작업해드립니다. 7일 이후에는 유료 A/S가 적용됩니다.'
    },
    {
      id: 3,
      category: 'service',
      question: '충전은 어떻게 하나요?',
      answer: '계정 충전은 신용카드, 계좌이체, 가상계좌 등 다양한 방법으로 가능합니다. 충전 후 즉시 사용하실 수 있습니다.'
    },
    {
      id: 4,
      category: 'service',
      question: '제공되는 서비스는 안전한가요?',
      answer: '모든 서비스는 안전한 방법으로 제공되며, 계정에 해를 끼치지 않습니다. 개인정보도 철저히 보호됩니다.'
    },
    {
      id: 5,
      category: 'service',
      question: '서비스 운영시간은 어떻게 되나요?',
      answer: '24시간 자동으로 서비스가 운영됩니다. 주문하신 시간에 관계없이 즉시 처리됩니다.'
    },
    {
      id: 6,
      category: 'service',
      question: '고객센터 운영시간은 어떻게 되나요?',
      answer: '고객센터는 평일 오전 9시부터 오후 6시까지 운영됩니다. 주말 및 공휴일에는 이메일로 문의해주세요.'
    },
    {
      id: 7,
      category: 'service',
      question: '주문을 했는데 주문확인은 언제 되나요?',
      answer: '주문 접수 후 5-10분 내에 주문확인 메일이 발송됩니다. 스팸메일함도 확인해주세요.'
    },
    {
      id: 8,
      category: 'service',
      question: '주문을 했는데 주문상태가 \'주문접수/주문대기\'로 나와요.',
      answer: '주문접수 상태는 정상적인 과정입니다. 작업이 시작되면 \'작업중\'으로 변경되며, 완료되면 \'작업완료\'로 표시됩니다.'
    },
    {
      id: 9,
      category: 'instagram',
      question: '유령팔로워 주문하기 전에 알아야 할 사항이 있나요?',
      answer: '유령팔로워는 실제 사용자가 아닌 가상 계정입니다. 계정 신뢰도 향상에는 도움이 되지만, 실제 상호작용은 기대하기 어렵습니다.'
    },
    {
      id: 10,
      category: 'instagram',
      question: '자동좋아요 입력란에 최소/최대 수량은 뭔가요?',
      answer: '자동좋아요는 게시물당 10개부터 1000개까지 설정 가능합니다. 수량이 많을수록 더 많은 좋아요를 받게 됩니다.'
    },
    {
      id: 11,
      category: 'instagram',
      question: '좋아요를 신청하면 몇 분만에 숫자가 올라가나요?',
      answer: '일반적으로 5-30분 내에 좋아요가 증가하기 시작합니다. 수량에 따라 완료까지 1-3시간 정도 소요됩니다.'
    },
    {
      id: 12,
      category: 'cancel-refund',
      question: '주문이 취소되었는데 어떻게 환불 받나요?',
      answer: '취소된 주문의 환불은 원래 결제 수단으로 자동 처리됩니다. 3-5일 내에 환불이 완료됩니다.'
    },
    {
      id: 13,
      category: 'cancel-refund',
      question: '포인트 환불 절차가 어떻게 되나요?',
      answer: '포인트 환불은 고객센터에 문의하시면 계좌이체로 처리해드립니다. 수수료 없이 전액 환불됩니다.'
    },
    {
      id: 14,
      category: 'service',
      question: '가격이 왜 이렇게 저렴한가요?',
      answer: '자동화된 시스템을 통해 운영비를 최소화하여 고객님께 합리적인 가격으로 서비스를 제공하고 있습니다.'
    },
    {
      id: 15,
      category: 'service',
      question: '실제 유저로 작업이 되나요?',
      answer: '모든 서비스는 실제 유저를 통해 작업됩니다. 가상 계정이나 봇을 사용하지 않습니다.'
    },
    {
      id: 16,
      category: 'service',
      question: '모바일 이용이 가능한가요?',
      answer: '네, 모바일에서도 모든 서비스를 이용하실 수 있습니다. 반응형 웹사이트로 최적화되어 있습니다.'
    },
    {
      id: 17,
      category: 'service',
      question: '서비스 사용중 다른 매체로 동시에 광고해도 되나요?',
      answer: '네, 다른 매체와 동시에 광고하셔도 됩니다. 각 플랫폼별로 독립적으로 서비스를 이용하실 수 있습니다.'
    },
    {
      id: 18,
      category: 'service',
      question: '같은 링크를 중복해서 또 주문할 수 있나요?',
      answer: '네, 같은 링크로 중복 주문이 가능합니다. 기존 작업과 별도로 추가 작업이 진행됩니다.'
    },
    {
      id: 19,
      category: 'service',
      question: '주문이 진행되다가 \'주문실패\'로 바뀌면 어떻게 되나요?',
      answer: '주문실패 시 자동으로 환불 처리되며, 고객센터에 문의하시면 재주문을 도와드립니다.'
    },
    {
      id: 20,
      category: 'service',
      question: '팔로워 or 좋아요가 주문수량보다 적게 들어왔는데, 주문내역 상태창에는 \'주문완료\'로 되어있습니다',
      answer: '수량이 부족한 경우 자동으로 보충 작업이 진행됩니다. 완전한 수량이 도달할 때까지 작업이 계속됩니다.'
    },
    {
      id: 21,
      category: 'instagram',
      question: '인스타그램 작업 기간은 얼마나 걸리나요?',
      answer: '일반적으로 1-3일 내에 작업이 완료됩니다. 수량이 많을수록 시간이 더 소요될 수 있습니다.'
    },
    {
      id: 22,
      category: 'instagram',
      question: '작업 속도를 조절할 수 있을까요?',
      answer: '네, 작업 속도 조절이 가능합니다. 빠른 작업과 천천히 진행하는 작업 중 선택하실 수 있습니다.'
    }
  ]

  const filteredFAQs = selectedCategory === 'all' 
    ? faqs 
    : faqs.filter(faq => faq.category === selectedCategory)

  return (
    <div className="faq-page">
      <div className="faq-header">
        <h1>자주 묻는 질문</h1>
        <p>고객님들이 자주 문의하시는 질문들을 모았습니다</p>
      </div>

      <div className="faq-categories">
        {categories.map((category) => (
          <button
            key={category.id}
            className={`category-btn ${selectedCategory === category.id ? 'active' : ''}`}
            onClick={() => setSelectedCategory(category.id)}
          >
            {category.name}
          </button>
        ))}
      </div>

      <div className="faq-content">
        <div className="faq-grid">
          {filteredFAQs.map((faq) => (
            <div key={faq.id} className="faq-item">
              <div 
                className="faq-question"
                onClick={() => toggleExpanded(faq.id)}
              >
                <span>{faq.question}</span>
                {expandedItems[faq.id] ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
              </div>
              
              {expandedItems[faq.id] && (
                <div className="faq-answer">
                  <p>{faq.answer}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default FAQPage
