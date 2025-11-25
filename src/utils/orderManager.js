// Order state management utility
export const createOrderData = ({
  type, // 'package' | 'product'
  category,
  product,
  variant,
  packageData,
  quantity,
  link,
  comments,
  scheduledDate,
  scheduledTime,
  splitDelivery
}) => {
  const baseOrder = {
    type,
    category: { id: category?.category_id, name: category?.name, slug: category?.category_slug },
    timestamp: new Date().toISOString()
  }

  if (type === 'package') {
    // packageData가 없으면 빈 패키지 반환
    if (!packageData) {
      console.warn('⚠️ packageData가 없습니다.')
      return {
        ...baseOrder,
        package: {
          id: null,
          name: '알 수 없는 패키지',
          description: '',
          items: [],
          steps: []
        },
        orderDetails: { link },
        pricing: { subtotal: 0, total: 0, formatted: '₩0' }
      }
    }
    
    // items 배열이 있으면 items 사용, 없으면 steps 사용
    const packageItems = packageData.items || packageData.steps || []
    
    return {
      ...baseOrder,
      package: {
        id: packageData.package_id,
        name: packageData.name,
        description: packageData.description,
        items: packageItems.map(item => ({
          package_item_id: item.package_item_id,
          step: item.step,
          variant_id: item.variant_id || item.id,
          variant_name: item.variant_name || item.name,
          quantity: item.quantity,
          repeat_count: item.repeat_count || item.repeat || 1,
          variant_price: item.variant_price || item.price,
          term_value: item.term_value || item.delay || 0,
          term_unit: item.term_unit || 'minute'
        })),
        steps: packageData.steps || []
      },
      orderDetails: { link },
      pricing: calculatePackagePrice(packageData)
    }
  }

  // Regular product order
  return {
    ...baseOrder,
    product: { id: product?.product_id, name: product?.name, is_domestic: product?.is_domestic },
    variant: {
      id: variant?.variant_id,
      name: variant?.name,
      min: variant?.min_quantity,
      max: variant?.max_quantity,
      price: variant?.price
    },
    orderDetails: {
      quantity,
      link,
      comments: comments || null,
      scheduled: scheduledDate && scheduledTime ? { date: scheduledDate, time: scheduledTime } : null,
      splitDelivery: splitDelivery ? { days: splitDelivery.days, dailyQuantity: splitDelivery.dailyQuantity } : null
    },
    pricing: calculateProductPrice(variant, quantity)
  }
}

const calculatePackagePrice = (packageData) => {
  // packageData가 없으면 0 반환
  if (!packageData) {
    return { subtotal: 0, total: 0, formatted: '₩0' }
  }
  
  // items 배열이 있으면 items 사용, 없으면 steps 사용
  const items = packageData.items || packageData.steps || []
  const total = items.reduce((sum, item) => {
    const price = parseFloat(item.variant_price || item.price || 0)
    const quantity = item.quantity || 0
    const repeat = item.repeat_count || item.repeat || 1
    return sum + (price * quantity * repeat)
  }, 0)
  return { subtotal: total, total: total, formatted: formatPrice(total) }
}

const calculateProductPrice = (variant, quantity) => {
  const pricePerUnit = parseFloat(variant?.price || 0)
  const subtotal = (pricePerUnit * quantity) / 1000
  return { subtotal, total: subtotal, pricePerUnit, quantity, formatted: formatPrice(subtotal) }
}

const formatPrice = (price) => {
  const formatted = price % 1 === 0 ? price.toString() : price.toFixed(2)
  return `₩${formatted}`
}

// Save to sessionStorage for checkout
export const saveOrderForCheckout = (orderData) => {
  try {
    sessionStorage.setItem('pendingOrder', JSON.stringify(orderData))
    return true
  } catch (error) {
    console.error('Failed to save order:', error)
    return false
  }
}

// Retrieve from sessionStorage
export const getOrderForCheckout = () => {
  try {
    const data = sessionStorage.getItem('pendingOrder')
    return data ? JSON.parse(data) : null
  } catch (error) {
    console.error('Failed to retrieve order:', error)
    return null
  }
}

// Clear order after completion
export const clearOrderCheckout = () => {
  sessionStorage.removeItem('pendingOrder')
}

