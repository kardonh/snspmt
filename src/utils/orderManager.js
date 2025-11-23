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
    return {
      ...baseOrder,
      package: {
        id: packageData.package_id,
        name: packageData.name,
        description: packageData.description,
        steps: packageData.steps?.map(step => ({
          step: step.step,
          variant_id: step.variant_id,
          variant_name: step.variant_name,
          quantity: step.quantity,
          repeat_count: step.repeat_count,
          price: step.variant_price,
          term: { value: step.term_value, unit: step.term_unit }
        })) || []
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
      id: variant?.id,
      name: variant?.name,
      min: variant?.min,
      max: variant?.max,
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
  const total = packageData.steps?.reduce((sum, step) => 
    sum + (parseFloat(step.variant_price) * step.quantity * step.repeat_count), 0) || 0
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

