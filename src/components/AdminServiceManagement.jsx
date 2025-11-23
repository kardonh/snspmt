import React, { useState, useEffect } from 'react'
import {
  Plus,
  Edit,
  Trash2,
  Package,
  Tag,
  Layers,
  X,
  Save,
  ChevronDown,
  ChevronRight,
  RefreshCw
} from 'lucide-react'
import CategoryManager from './admin_service/CategoryManager'
import ProductManager from './admin_service/ProductManager'
import VariantManager from './admin_service/VariantManager'
import PackageManager from './admin_service/PackageManager'
import './AdminServiceManagement.css'

const AdminServiceManagement = ({ adminFetch }) => {
  const [categories, setCategories] = useState([])
  const [products, setProducts] = useState([])
  const [variants, setVariants] = useState([])
  const [packages, setPackages] = useState([])
  const [selectedCategoryId, setSelectedCategoryId] = useState(null)
  const [selectedProductId, setSelectedProductId] = useState(null)
  const [expandedCategories, setExpandedCategories] = useState(new Set())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // 모달 상태
  const [showCategoryModal, setShowCategoryModal] = useState(false)
  const [showProductModal, setShowProductModal] = useState(false)
  const [showVariantModal, setShowVariantModal] = useState(false)
  const [showPackageModal, setShowPackageModal] = useState(false)
  const [editingItem, setEditingItem] = useState(null)

  // 폼 상태
  const [categoryForm, setCategoryForm] = useState({
    name: '',
    slug: '',
    image_url: '',
    is_active: true
  })
  const [productForm, setProductForm] = useState({
    category_id: null,
    name: '',
    description: '',
    is_domestic: true,
    is_auto: false,  // 자동상품 여부
    auto_tag: false,
    is_package: false
  })
  const [variantForm, setVariantForm] = useState({
    category_id: null,  // 카테고리 ?�택 추�?
    product_id: null,
    name: '',
    price: '',
    min_quantity: '',
    max_quantity: '',
    delivery_time_days: '',
    description: '',  // 상세정보
    time: '',  // 배송 시간 문자열 (예: "14시간 54분")
    smm_service_id: '',  // SMM Panel 서비스 ID
    drip_feed: false,  // Drip-feed 여부
    runs: '',  // Drip-feed 실행 횟수
    interval: '',  // Drip-feed 간격 (분)
    drip_quantity: '',  // Drip-feed 수량
    is_active: true,
    meta_json: {},
    api_endpoint: '',
    // 추가 정보 입력 필드 설정
    requires_comments: false,
    requires_custom_fields: false,
    custom_fields_config: {}
  })
  const [packageForm, setPackageForm] = useState({
    category_id: null,
    name: '',
    description: '',
    price: '',  // 패키지 가격
    min_quantity: '',  // 최소 수량
    max_quantity: '',  // 최대 수량
    time: '',  // 배송 시간 문자열 (예: "24-48시간", "30일")
    smmkings_id: '',  // SMM Panel 서비스 ID (drip-feed 패키지용)
    drip_feed: false,  // Drip-feed 여부
    runs: '',  // Drip-feed 실행 횟수
    interval: '',  // Drip-feed 간격 (분)
    drip_quantity: '',  // Drip-feed 수량
    items: []
  })

  // 데이터 로드
  useEffect(() => {
    loadCategories()
    loadProducts()
    loadVariants()
    loadPackages()
    
    // SMM API 엔드포인트 환경변수에서 자동 로드
    const loadSmmEndpoint = async () => {
      try {
        const response = await adminFetch('/api/admin/config')
        if (response.ok) {
          const data = await response.json()
          if (data.smm_api_endpoint && !variantForm.api_endpoint) {
            setVariantForm(prev => ({ ...prev, api_endpoint: data.smm_api_endpoint }))
          }
        }
      } catch (err) {
        console.error('SMM API 엔드포인트 로드 실패:', err)
      }
    }
    loadSmmEndpoint()
  }, [])

  useEffect(() => {
    if (
      selectedCategoryId &&
      !categories.some((category) => category.category_id === selectedCategoryId)
    ) {
      setSelectedCategoryId(null)
      setSelectedProductId(null)
    }
  }, [categories, selectedCategoryId])

  useEffect(() => {
    if (
      selectedProductId &&
      !products.some(
        (product) =>
          product.product_id === selectedProductId &&
          (!selectedCategoryId || product.category_id === selectedCategoryId)
      )
    ) {
      setSelectedProductId(null)
    }
  }, [products, selectedCategoryId, selectedProductId])

  const importSMM = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await adminFetch('/api/admin/catalog/import-smm', {
        method: 'POST'
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(data?.error || 'SMM 동기화 실패')
      }
      // 동기화 후 카탈로그 새로고침
      await Promise.all([loadCategories(), loadProducts(), loadVariants()])
      alert(data?.message || 'SMM 서비스 동기화 완료')
    } catch (e) {
      console.error('SMM 동기화 오류:', e)
      setError(e.message || 'SMM 동기화 오류')
      alert(e.message || 'SMM 동기화 오류')
    } finally {
      setLoading(false)
    }
  }

  const loadCategories = async () => {
    try {
      const response = await adminFetch('/api/admin/categories?include_inactive=true')
      if (response.ok) {
        const data = await response.json()
        setCategories(data.categories || [])
      }
    } catch (err) {
      console.error('카테고리 로드 실패:', err)
    }
  }

  const loadProducts = async () => {
    try {
      const response = await adminFetch('/api/admin/products')
      if (response.ok) {
        const data = await response.json()
        setProducts(data.products || [])
      }
    } catch (err) {
      console.error('상품 로드 실패:', err)
    }
  }

  const loadVariants = async () => {
    try {
      const response = await adminFetch('/api/admin/product-variants')
      if (response.ok) {
        const data = await response.json()
        setVariants(data.variants || [])
      }
    } catch (err) {
      console.error('옵션 로드 실패:', err)
    }
  }

  const loadPackages = async () => {
    try {
      const response = await adminFetch('/api/admin/packages')
      if (response.ok) {
        const data = await response.json()
        setPackages(data.packages || [])
      }
    } catch (err) {
      console.error('패키지 로드 실패:', err)
    }
  }

  const handleSelectCategory = (categoryId) => {
    setSelectedCategoryId(categoryId)
    setSelectedProductId(null)
  }

  const handleSelectProduct = (productId) => {
    setSelectedProductId(productId)
  }

  // 카테고리 ?��?
  const toggleCategory = (categoryId) => {
    const newExpanded = new Set(expandedCategories)
    if (newExpanded.has(categoryId)) {
      newExpanded.delete(categoryId)
    } else {
      newExpanded.add(categoryId)
    }
    setExpandedCategories(newExpanded)
  }

  // 카테고리�??�품 ?�터�?
  const getProductsByCategory = (categoryId) => {
    return products.filter(p => p.category_id === categoryId)
  }

  // ?�품�??�션 ?�터�?
  const getVariantsByProduct = (productId) => {
    return variants.filter(v => v.product_id === productId)
  }

  // 카테고리 추�?/수정
  const handleCategorySubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const url = editingItem
        ? `/api/admin/categories/${editingItem.category_id}`
        : `/api/admin/categories`
      
      const method = editingItem ? 'PUT' : 'POST'
      
      const response = await adminFetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(categoryForm)
      })

      if (response.ok) {
        await loadCategories()
        setShowCategoryModal(false)
        setEditingItem(null)
        setCategoryForm({ name: '', slug: '', image_url: '', is_active: true })
      } else {
        const data = await response.json()
        setError(data.error || '카테고리 저장 실패')
      }
    } catch (err) {
      setError('카테고리 저장 중 오류 발생')
    } finally {
      setLoading(false)
    }
  }

  // ?�품 추�?/수정
  const handleProductSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const url = editingItem
        ? `/api/admin/products/${editingItem.product_id}`
        : `/api/admin/products`
      
      const method = editingItem ? 'PUT' : 'POST'
      
      const response = await adminFetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category_id: parseInt(productForm.category_id),
          name: productForm.name,
          description: productForm.description,
          is_domestic: productForm.is_domestic,
          is_auto: productForm.is_auto,
          auto_tag: productForm.auto_tag
        })
      })

      if (response.ok) {
        await loadProducts()
        setShowProductModal(false)
        setEditingItem(null)
        setProductForm({
          category_id: null,
          name: '',
          description: '',
          is_domestic: true,
          is_auto: false,
          auto_tag: false,
          is_package: false
        })
      } else {
        const data = await response.json()
        setError(data.error || '상품 저장 실패')
      }
    } catch (err) {
      setError('상품 저장 중 오류 발생')
    } finally {
      setLoading(false)
    }
  }

  // 세부서비스 추가/수정
  const handleVariantSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const url = editingItem
        ? `/api/admin/product-variants/${editingItem.variant_id}`
        : `/api/admin/product-variants`
      
      const method = editingItem ? 'PUT' : 'POST'
      
      // meta_json 구성 (추가 정보 입력 필드 설정 포함)
      const metaJson = {
        ...(variantForm.meta_json || {}),
        description: variantForm.description || null,
        time: variantForm.time || null,
        smm_service_id: variantForm.smm_service_id ? parseInt(variantForm.smm_service_id) : null,
        id: variantForm.smm_service_id ? parseInt(variantForm.smm_service_id) : null,  // 하위 호환성
        drip_feed: variantForm.drip_feed || false,
        runs: variantForm.runs ? parseInt(variantForm.runs) : null,
        interval: variantForm.interval ? parseInt(variantForm.interval) : null,
        drip_quantity: variantForm.drip_quantity ? parseInt(variantForm.drip_quantity) : null,
        // 추가 정보 입력 필드 설정
        requires_comments: variantForm.requires_comments || false,
        requires_custom_fields: variantForm.requires_custom_fields || false,
        custom_fields_config: variantForm.custom_fields_config || {}
      }
      
      // null 값 제거
      Object.keys(metaJson).forEach(key => {
        if (metaJson[key] === null || metaJson[key] === '') {
          delete metaJson[key]
        }
      })

      const response = await adminFetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: parseInt(variantForm.product_id),
          name: variantForm.name,
          price: parseFloat(variantForm.price),
          min_quantity: variantForm.min_quantity ? parseInt(variantForm.min_quantity) : null,
          max_quantity: variantForm.max_quantity ? parseInt(variantForm.max_quantity) : null,
          delivery_time_days: variantForm.delivery_time_days ? parseInt(variantForm.delivery_time_days) : null,
          is_active: variantForm.is_active,
          meta_json: metaJson,
          api_endpoint: variantForm.api_endpoint || null
        })
      })

      if (response.ok) {
        await loadVariants()
        setShowVariantModal(false)
        setEditingItem(null)
        setVariantForm({
          category_id: null,
          product_id: null,
          name: '',
          price: '',
          min_quantity: '',
          max_quantity: '',
          delivery_time_days: '',
          description: '',
          time: '',
          smm_service_id: '',
          drip_feed: false,
          runs: '',
          interval: '',
          drip_quantity: '',
          is_active: true,
          meta_json: {},
          api_endpoint: '',
          requires_comments: false,
          requires_custom_fields: false,
          custom_fields_config: {}
        })
      } else {
        const data = await response.json()
        setError(data.error || '옵션 저장 실패')
      }
    } catch (err) {
      setError('옵션 저장 중 오류 발생')
    } finally {
      setLoading(false)
    }
  }

  // 삭제 함수들
  const handleDeleteCategory = async (categoryId) => {
    if (!confirm('카테고리를 삭제하시겠습니까?\n\n연결된 상품이나 패키지도 함께 삭제될 수 있습니다.')) return

    try {
      const response = await adminFetch(`/api/admin/categories/${categoryId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        const data = await response.json()
        alert(data.message || '카테고리가 삭제되었습니다.')
        await loadCategories()
        await loadProducts()
        await loadVariants()
        await loadPackages()
      } else {
        const errorData = await response.json()
        alert(errorData.error || '카테고리 삭제 실패')
      }
    } catch (err) {
      console.error('카테고리 삭제 실패:', err)
      alert('카테고리 삭제 중 오류가 발생했습니다.')
    }
  }

  const handleDeleteProduct = async (productId) => {
    if (!confirm('상품을 삭제하시겠습니까?')) return

    try {
      const response = await adminFetch(`/api/admin/products/${productId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        await loadProducts()
        await loadVariants()
      } else {
        const data = await response.json()
        alert(data.error || '상품 삭제 실패')
      }
    } catch (err) {
      console.error('상품 삭제 실패:', err)
    }
  }

  const handleDeleteVariant = async (variantId) => {
    if (!confirm('옵션을 삭제하시겠습니까?')) return

    try {
      const response = await adminFetch(`/api/admin/product-variants/${variantId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        await loadVariants()
      }
    } catch (err) {
      console.error('옵션 삭제 실패:', err)
    }
  }

  const handleDeletePackage = async (packageId) => {
    if (!confirm('패키지를 삭제하시겠습니까?')) return

    try {
      const response = await adminFetch(`/api/admin/packages/${packageId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        await loadPackages()
      } else {
        const data = await response.json()
        alert(data.error || '패키지 삭제 실패')
      }
    } catch (err) {
      console.error('패키지 삭제 실패:', err)
      alert('패키지 삭제 중 오류가 발생했습니다.')
    }
  }

  // 모달 열기 함수들
  const openCategoryModal = (category = null) => {
    if (category) {
      setEditingItem(category)
      setCategoryForm({
        name: category.name,
        slug: category.slug || '',
        image_url: category.image_url || '',
        is_active: category.is_active
      })
    } else {
      setEditingItem(null)
      setCategoryForm({ name: '', slug: '', image_url: '', is_active: true })
    }
    setShowCategoryModal(true)
  }

  const openProductModal = (product = null, categoryId = null) => {
    if (product) {
      setEditingItem(product)
      setProductForm({
        category_id: product.category_id,
        name: product.name,
        description: product.description || '',
        is_domestic: product.is_domestic,
        is_auto: product.is_auto || false,
        auto_tag: product.auto_tag || false,
        is_package: false
      })
    } else {
      setEditingItem(null)
      setProductForm({
        category_id: categoryId || selectedCategoryId || null,
        name: '',
        description: '',
        is_domestic: true,
        is_auto: false,
        auto_tag: false,
        is_package: false
      })
    }
    setShowProductModal(true)
  }

  const openVariantModal = (variant = null, productId = null, categoryId = null) => {
    if (variant) {
      setEditingItem(variant)
      // variant?�서 product_id�??�품 찾기
      const product = products.find(p => p.product_id === variant.product_id)
      const catId = product ? product.category_id : null
      
      const meta = variant.meta_json || {}
      setVariantForm({
        category_id: catId,
        product_id: variant.product_id,
        name: variant.name,
        price: variant.price,
        min_quantity: variant.min_quantity || '',
        max_quantity: variant.max_quantity || '',
        delivery_time_days: variant.delivery_time_days || '',
        description: meta.description || '',
        time: meta.time || '',
        smm_service_id: meta.smm_service_id || meta.id || '',
        drip_feed: meta.drip_feed || false,
        runs: meta.runs || '',
        interval: meta.interval || '',
        drip_quantity: meta.drip_quantity || '',
        is_active: variant.is_active,
        meta_json: variant.meta_json || {},
        api_endpoint: variant.api_endpoint || '',
        // 추가 정보 입력 필드 설정
        requires_comments: (meta.requires_comments) || false,
        requires_custom_fields: (meta.requires_custom_fields) || false,
        custom_fields_config: (meta.custom_fields_config) || {}
      })
    } else {
      setEditingItem(null)
      setVariantForm({
        category_id: categoryId || selectedCategoryId || null,
        product_id: productId || selectedProductId || null,
        name: '',
        price: '',
        min_quantity: '',
        max_quantity: '',
        delivery_time_days: '',
        description: '',
        time: '',
        smm_service_id: '',
        drip_feed: false,
        runs: '',
        interval: '',
        drip_quantity: '',
        is_active: true,
        meta_json: {},
        api_endpoint: '',
        requires_comments: false,
        requires_custom_fields: false,
        custom_fields_config: {}
      })
    }
    setShowVariantModal(true)
  }

  // 카테고리 ?�택 ???�당 카테고리???�품�??�터�?
  const getProductsBySelectedCategory = () => {
    if (!variantForm.category_id) return []
    return products.filter(p => p.category_id === parseInt(variantForm.category_id))
  }

  const openPackageModal = (pkg = null) => {
    if (pkg) {
      setEditingItem(pkg)
      const meta = pkg.meta_json || {}
      setPackageForm({
        category_id: pkg.category_id,
        name: pkg.name,
        description: pkg.description || '',
        price: meta.price || pkg.price || '',
        min_quantity: meta.min || meta.min_quantity || '',
        max_quantity: meta.max || meta.max_quantity || '',
        time: meta.time || '',
        smmkings_id: meta.smmkings_id || meta.id || '',
        drip_feed: meta.drip_feed || false,
        runs: meta.runs || '',
        interval: meta.interval || '',
        drip_quantity: meta.drip_quantity || '',
        items: pkg.items || []
      })
    } else {
      setEditingItem(null)
      setPackageForm({
        category_id: null,
        name: '',
        description: '',
        price: '',
        min_quantity: '',
        max_quantity: '',
        time: '',
        smmkings_id: '',
        drip_feed: false,
        runs: '',
        interval: '',
        drip_quantity: '',
        items: []
      })
    }
    setShowPackageModal(true)
  }

  // ?�키지 추�?/수정
  const handlePackageSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const url = editingItem
        ? `/api/admin/packages/${editingItem.package_id}`
        : `/api/admin/packages`
      
      const method = editingItem ? 'PUT' : 'POST'
      
      // meta_json 구성
      const metaJson = {
        price: packageForm.price ? parseFloat(packageForm.price) : null,
        min: packageForm.min_quantity ? parseInt(packageForm.min_quantity) : null,
        min_quantity: packageForm.min_quantity ? parseInt(packageForm.min_quantity) : null,
        max: packageForm.max_quantity ? parseInt(packageForm.max_quantity) : null,
        max_quantity: packageForm.max_quantity ? parseInt(packageForm.max_quantity) : null,
        time: packageForm.time || null,
        smmkings_id: packageForm.smmkings_id ? parseInt(packageForm.smmkings_id) : null,
        id: packageForm.smmkings_id ? parseInt(packageForm.smmkings_id) : null,  // 하위 호환성
        drip_feed: packageForm.drip_feed || false,
        runs: packageForm.runs ? parseInt(packageForm.runs) : null,
        interval: packageForm.interval ? parseInt(packageForm.interval) : null,
        drip_quantity: packageForm.drip_quantity ? parseInt(packageForm.drip_quantity) : null
      }
      
      // null 값 제거
      Object.keys(metaJson).forEach(key => {
        if (metaJson[key] === null || metaJson[key] === '') {
          delete metaJson[key]
        }
      })

      const response = await adminFetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category_id: parseInt(packageForm.category_id),
          name: packageForm.name,
          description: packageForm.description,
          meta_json: Object.keys(metaJson).length > 0 ? metaJson : null,
          items: packageForm.items
        })
      })

      if (response.ok) {
        await loadPackages()
        setShowPackageModal(false)
        setEditingItem(null)
        setPackageForm({
          category_id: null,
          name: '',
          description: '',
          price: '',
          min_quantity: '',
          max_quantity: '',
          time: '',
          smmkings_id: '',
          drip_feed: false,
          runs: '',
          interval: '',
          drip_quantity: '',
          items: []
        })
      } else {
        const data = await response.json()
        setError(data.error || '?�키지 ?�???�패')
      }
    } catch (err) {
      setError('?�키지 ?�??�??�류 발생')
    } finally {
      setLoading(false)
    }
  }

  // ?�키지 ?�이??추�?
  const addPackageItem = () => {
    setPackageForm({
      ...packageForm,
      items: [
        ...packageForm.items,
        {
          variant_id: null,
          step: packageForm.items.length + 1,
          term_value: null,
          term_unit: 'day',
          quantity: null,
          repeat_count: null,
          repeat_term_value: null,
          repeat_term_unit: 'day'
        }
      ]
    })
  }

  // ?�키지 ?�이???�거
  const removePackageItem = (index) => {
    const newItems = packageForm.items.filter((_, i) => i !== index)
    // step 수정??
    newItems.forEach((item, i) => {
      item.step = i + 1
    })
    setPackageForm({
      ...packageForm,
      items: newItems
    })
  }

  // ?�키지 ?�이???�데?�트
  const updatePackageItem = (index, field, value) => {
    const newItems = [...packageForm.items]
    newItems[index] = {
      ...newItems[index],
      [field]: value
    }
    setPackageForm({
      ...packageForm,
      items: newItems
    })
  }

  return (
    <div className="admin-service-management">
      <div className="service-header">
        <div>
          <h2>서비스 관리</h2>
          <p className="service-subtitle">
            카테고리 → 상품 → 세부서비스 → 패키지 순서로 구성하세요.
          </p>
        </div>
        <div className="header-actions">
          <button className="btn-secondary" onClick={importSMM} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'spinning' : ''} />
            SMM 서비스 동기화
          </button>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="service-flow-grid">
        <CategoryManager
          categories={categories}
          selectedCategoryId={selectedCategoryId}
          onSelectCategory={handleSelectCategory}
          onAddCategory={() => openCategoryModal()}
          onEditCategory={openCategoryModal}
          onDeleteCategory={handleDeleteCategory}
        />
        <ProductManager
          categories={categories}
          products={products}
          selectedCategoryId={selectedCategoryId}
          selectedProductId={selectedProductId}
          onSelectProduct={handleSelectProduct}
          onAddProduct={(categoryId) => openProductModal(null, categoryId)}
          onEditProduct={openProductModal}
          onDeleteProduct={handleDeleteProduct}
          onAddVariant={(productId, categoryId) => openVariantModal(null, productId, categoryId)}
        />
        <VariantManager
          variants={variants}
          products={products}
          selectedProductId={selectedProductId}
          onAddVariant={(productId, categoryId) => openVariantModal(null, productId, categoryId)}
          onEditVariant={openVariantModal}
          onDeleteVariant={handleDeleteVariant}
        />
      </div>

      <PackageManager
        packages={packages}
        categories={categories}
        onAddPackage={() => openPackageModal()}
        onEditPackage={openPackageModal}
        onDeletePackage={handleDeletePackage}
      />

      <div className="section-header" style={{ marginTop: '40px' }}>
        <h3>전체 서비스 구조</h3>
        <p>트리 구조로 한눈에 확인하세요.</p>
      </div>


      {/* 카테고리 모달 */}
      {showCategoryModal && (
        <div className="modal-overlay" onClick={() => setShowCategoryModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingItem ? '카테고리 수정' : '카테고리 추가'}</h3>
              <button className="btn-icon" onClick={() => setShowCategoryModal(false)}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleCategorySubmit}>
              <div className="form-group">
                <label>카테고리 이름 *</label>
                <input
                  type="text"
                  value={categoryForm.name}
                  onChange={(e) => setCategoryForm({ ...categoryForm, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>슬러그</label>
                <input
                  type="text"
                  value={categoryForm.slug}
                  onChange={(e) => setCategoryForm({ ...categoryForm, slug: e.target.value })}
                  placeholder="자동 생성됨"
                />
              </div>
              <div className="form-group">
                <label>이미지 URL</label>
                <input
                  type="url"
                  value={categoryForm.image_url}
                  onChange={(e) => setCategoryForm({ ...categoryForm, image_url: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={categoryForm.is_active}
                    onChange={(e) => setCategoryForm({ ...categoryForm, is_active: e.target.checked })}
                  />
                  활성화
                </label>
              </div>
              <div className="modal-actions">
                <button type="button" onClick={() => setShowCategoryModal(false)}>
                  취소
                </button>
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? '저장 중...' : '저장'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 상품 모달 */}
      {showProductModal && (
        <div className="modal-overlay" onClick={() => setShowProductModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingItem ? '상품 수정' : '상품 추가'}</h3>
              <button className="btn-icon" onClick={() => setShowProductModal(false)}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleProductSubmit}>
              <div className="form-group">
                <label>카테고리 *</label>
                <select
                  value={productForm.category_id || ''}
                  onChange={(e) => setProductForm({ ...productForm, category_id: e.target.value })}
                  required
                >
                  <option value="">선택하세요</option>
                  {categories.filter(c => c.is_active).map(cat => (
                    <option key={cat.category_id} value={cat.category_id}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>상품 이름 *</label>
                <input
                  type="text"
                  value={productForm.name}
                  onChange={(e) => setProductForm({ ...productForm, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>설명</label>
                <textarea
                  value={productForm.description}
                  onChange={(e) => setProductForm({ ...productForm, description: e.target.value })}
                  rows={3}
                />
              </div>
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={productForm.is_domestic}
                    onChange={(e) => setProductForm({ ...productForm, is_domestic: e.target.checked })}
                  />
                  국내 서비스
                </label>
              </div>
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={productForm.is_auto}
                    onChange={(e) => setProductForm({ ...productForm, is_auto: e.target.checked })}
                  />
                  자동상품
                </label>
                {productForm.is_auto && (
                  <span className="badge" style={{ marginLeft: '8px', padding: '4px 8px', backgroundColor: '#4CAF50', color: 'white', borderRadius: '4px', fontSize: '12px' }}>
                    자동
                  </span>
                )}
              </div>
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={productForm.auto_tag}
                    onChange={(e) => setProductForm({ ...productForm, auto_tag: e.target.checked })}
                  />
                  자동 태그
                </label>
                {productForm.auto_tag && (
                  <span className="badge" style={{ marginLeft: '8px', padding: '4px 8px', backgroundColor: '#2196F3', color: 'white', borderRadius: '4px', fontSize: '12px' }}>
                    자동 태그
                  </span>
                )}
              </div>
              <div className="modal-actions">
                <button type="button" onClick={() => setShowProductModal(false)}>
                  취소
                </button>
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? '저장 중...' : '저장'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 세부서비스 모달 */}
      {showVariantModal && (
        <div className="modal-overlay" onClick={() => setShowVariantModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '700px', maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="modal-header">
              <h3>{editingItem ? '세부서비스 수정' : '세부서비스 추가'}</h3>
              <button className="btn-icon" onClick={() => setShowVariantModal(false)}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleVariantSubmit}>
              <div className="form-group">
                <label>카테고리 *</label>
                <select
                  value={variantForm.category_id || ''}
                  onChange={(e) => setVariantForm({ ...variantForm, category_id: e.target.value, product_id: null })}
                  required
                >
                  <option value="">선택하세요</option>
                  {categories.filter(c => c.is_active).map(cat => (
                    <option key={cat.category_id} value={cat.category_id}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>상품 *</label>
                <select
                  value={variantForm.product_id || ''}
                  onChange={(e) => setVariantForm({ ...variantForm, product_id: e.target.value })}
                  required
                  disabled={!variantForm.category_id}
                >
                  <option value="">선택하세요</option>
                  {getProductsBySelectedCategory().map(prod => (
                    <option key={prod.product_id} value={prod.product_id}>
                      {prod.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>세부서비스 이름 *</label>
                <input
                  type="text"
                  value={variantForm.name}
                  onChange={(e) => setVariantForm({ ...variantForm, name: e.target.value })}
                  placeholder="예: KR 인스타그램 한국인 ❤️ 파워업 좋아요"
                  required
                />
              </div>
              <div className="form-group">
                <label>가격 *</label>
                <input
                  type="number"
                  value={variantForm.price}
                  onChange={(e) => setVariantForm({ ...variantForm, price: e.target.value })}
                  placeholder="예: 20000"
                  required
                  min="0"
                  step="0.01"
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>최소 수량</label>
                  <input
                    type="number"
                    value={variantForm.min_quantity}
                    onChange={(e) => setVariantForm({ ...variantForm, min_quantity: e.target.value })}
                    placeholder="예: 30"
                    min="0"
                  />
                </div>
                <div className="form-group">
                  <label>최대 수량</label>
                  <input
                    type="number"
                    value={variantForm.max_quantity}
                    onChange={(e) => setVariantForm({ ...variantForm, max_quantity: e.target.value })}
                    placeholder="예: 2500"
                    min="0"
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>배송 시간 (일)</label>
                  <input
                    type="number"
                    value={variantForm.delivery_time_days}
                    onChange={(e) => setVariantForm({ ...variantForm, delivery_time_days: e.target.value })}
                    placeholder="예: 1"
                    min="0"
                  />
                </div>
                <div className="form-group">
                  <label>배송 시간 (문자열)</label>
                  <input
                    type="text"
                    value={variantForm.time}
                    onChange={(e) => setVariantForm({ ...variantForm, time: e.target.value })}
                    placeholder="예: 14시간 54분"
                  />
                </div>
              </div>
              <div className="form-group">
                <label>상세정보 (Description)</label>
                <textarea
                  value={variantForm.description}
                  onChange={(e) => setVariantForm({ ...variantForm, description: e.target.value })}
                  placeholder="서비스 상세 설명"
                  rows={3}
                />
              </div>
              <div className="form-group">
                <label>SMM Panel 서비스 ID</label>
                <input
                  type="number"
                  value={variantForm.smm_service_id}
                  onChange={(e) => setVariantForm({ ...variantForm, smm_service_id: e.target.value })}
                  placeholder="예: 122"
                  min="0"
                />
              </div>
              <div className="form-group">
                <label>API 엔드포인트</label>
                <input
                  type="text"
                  value={variantForm.api_endpoint}
                  onChange={(e) => setVariantForm({ ...variantForm, api_endpoint: e.target.value })}
                  placeholder="SMM Panel API 엔드포인트 (환경변수에서 자동 로드)"
                />
                <small style={{ color: '#666', fontSize: '12px', display: 'block', marginTop: '4px' }}>
                  환경변수 SMMPANEL_API_ENDPOINT에서 자동으로 로드됩니다. 필요시 수동으로 수정할 수 있습니다.
                </small>
              </div>

              {/* 추가 정보 입력 필드 설정 */}
              <div className="form-section">
                <h4>추가 정보 입력 필드 설정</h4>
                <div className="form-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={variantForm.requires_comments || false}
                      onChange={(e) => setVariantForm({ ...variantForm, requires_comments: e.target.checked })}
                    />
                    댓글 필드 필요
                  </label>
                  <small style={{ color: '#666', fontSize: '12px', display: 'block', marginTop: '4px' }}>
                    주문 시 댓글을 입력받습니다
                  </small>
                </div>
                <div className="form-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={variantForm.requires_custom_fields || false}
                      onChange={(e) => setVariantForm({ ...variantForm, requires_custom_fields: e.target.checked })}
                    />
                    커스텀 필드 필요
                  </label>
                  <small style={{ color: '#666', fontSize: '12px', display: 'block', marginTop: '4px' }}>
                    주문 시 추가 정보를 입력받습니다
                  </small>
                </div>
                {variantForm.requires_custom_fields && (
                  <div className="form-group">
                    <label>커스텀 필드 설정 (JSON)</label>
                    <textarea
                      value={typeof variantForm.custom_fields_config === 'string' 
                        ? variantForm.custom_fields_config 
                        : JSON.stringify(variantForm.custom_fields_config || {}, null, 2)}
                      onChange={(e) => {
                        try {
                          const parsed = JSON.parse(e.target.value)
                          setVariantForm({ ...variantForm, custom_fields_config: parsed })
                        } catch {
                          setVariantForm({ ...variantForm, custom_fields_config: e.target.value })
                        }
                      }}
                      placeholder='{"field1": {"label": "필드명", "type": "text", "required": true}, ...}'
                      rows={4}
                      style={{ fontFamily: 'monospace', fontSize: '12px' }}
                    />
                      <small style={{ color: '#666', fontSize: '12px', display: 'block', marginTop: '4px' }}>
                        JSON 형식으로 커스텀 필드를 설정합니다. 예: &#123;"field1": &#123;"label": "사용자명", "type": "text", "required": true&#125;&#125;
                      </small>
                  </div>
                )}
              </div>
              
              {/* Drip-feed 설정 */}
              <div className="form-section">
                <h4>Drip-feed 설정</h4>
                <div className="form-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={variantForm.drip_feed}
                      onChange={(e) => setVariantForm({ ...variantForm, drip_feed: e.target.checked })}
                    />
                    Drip-feed 사용
                  </label>
                </div>
                {variantForm.drip_feed && (
                  <>
                    <div className="form-row">
                      <div className="form-group">
                        <label>실행 횟수 (runs)</label>
                        <input
                          type="number"
                          value={variantForm.runs}
                          onChange={(e) => setVariantForm({ ...variantForm, runs: e.target.value })}
                          placeholder="예: 30"
                          min="1"
                        />
                      </div>
                      <div className="form-group">
                        <label>간격 (분)</label>
                        <input
                          type="number"
                          value={variantForm.interval}
                          onChange={(e) => setVariantForm({ ...variantForm, interval: e.target.value })}
                          placeholder="예: 1440"
                          min="1"
                        />
                      </div>
                    </div>
                    <div className="form-group">
                      <label>Drip-feed 수량</label>
                      <input
                        type="number"
                        value={variantForm.drip_quantity}
                        onChange={(e) => setVariantForm({ ...variantForm, drip_quantity: e.target.value })}
                        placeholder="예: 400"
                        min="1"
                      />
                    </div>
                  </>
                )}
              </div>

              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={variantForm.is_active}
                    onChange={(e) => setVariantForm({ ...variantForm, is_active: e.target.checked })}
                  />
                  활성화
                </label>
              </div>

              {error && (
                <div className="error-message" style={{ marginTop: '16px' }}>
                  {error}
                </div>
              )}

              <div className="modal-actions">
                <button type="button" onClick={() => setShowVariantModal(false)}>
                  취소
                </button>
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? '저장 중...' : '저장'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 패키지 모달 */}
      {showPackageModal && (
        <div className="modal-overlay" onClick={() => setShowPackageModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '800px', maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="modal-header">
              <h3>{editingItem ? '패키지 수정' : '패키지 추가'}</h3>
              <button className="btn-icon" onClick={() => setShowPackageModal(false)}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handlePackageSubmit}>
              <div className="form-group">
                <label>카테고리 *</label>
                <select
                  value={packageForm.category_id || ''}
                  onChange={(e) => setPackageForm({ ...packageForm, category_id: e.target.value })}
                  required
                >
                  <option value="">선택하세요</option>
                  {categories.filter(c => c.is_active).map(cat => (
                    <option key={cat.category_id} value={cat.category_id}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>패키지 이름 *</label>
                <input
                  type="text"
                  value={packageForm.name}
                  onChange={(e) => setPackageForm({ ...packageForm, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>설명</label>
                <textarea
                  value={packageForm.description}
                  onChange={(e) => setPackageForm({ ...packageForm, description: e.target.value })}
                  rows={3}
                />
              </div>

              <div className="form-group">
                <label>패키지 가격</label>
                <input
                  type="number"
                  value={packageForm.price}
                  onChange={(e) => setPackageForm({ ...packageForm, price: e.target.value })}
                  placeholder="예: 20000000"
                  min="0"
                  step="0.01"
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>최소 수량</label>
                  <input
                    type="number"
                    value={packageForm.min_quantity}
                    onChange={(e) => setPackageForm({ ...packageForm, min_quantity: e.target.value })}
                    placeholder="예: 1"
                    min="0"
                  />
                </div>
                <div className="form-group">
                  <label>최대 수량</label>
                  <input
                    type="number"
                    value={packageForm.max_quantity}
                    onChange={(e) => setPackageForm({ ...packageForm, max_quantity: e.target.value })}
                    placeholder="예: 1"
                    min="0"
                  />
                </div>
              </div>

              <div className="form-group">
                <label>배송 시간 (문자열)</label>
                <input
                  type="text"
                  value={packageForm.time}
                  onChange={(e) => setPackageForm({ ...packageForm, time: e.target.value })}
                  placeholder="예: 24-48시간, 30일"
                />
              </div>

              {/* Drip-feed 설정 */}
              <div className="form-section">
                <h4>Drip-feed 설정</h4>
                <div className="form-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={packageForm.drip_feed}
                      onChange={(e) => setPackageForm({ ...packageForm, drip_feed: e.target.checked })}
                    />
                    Drip-feed 사용
                  </label>
                </div>
                {packageForm.drip_feed && (
                  <>
                    <div className="form-group">
                      <label>SMM Panel 서비스 ID (smmkings_id)</label>
                      <input
                        type="number"
                        value={packageForm.smmkings_id}
                        onChange={(e) => setPackageForm({ ...packageForm, smmkings_id: e.target.value })}
                        placeholder="예: 515"
                        min="0"
                      />
                    </div>
                    <div className="form-row">
                      <div className="form-group">
                        <label>실행 횟수 (runs)</label>
                        <input
                          type="number"
                          value={packageForm.runs}
                          onChange={(e) => setPackageForm({ ...packageForm, runs: e.target.value })}
                          placeholder="예: 30"
                          min="1"
                        />
                      </div>
                      <div className="form-group">
                        <label>간격 (분)</label>
                        <input
                          type="number"
                          value={packageForm.interval}
                          onChange={(e) => setPackageForm({ ...packageForm, interval: e.target.value })}
                          placeholder="예: 1440"
                          min="1"
                        />
                      </div>
                    </div>
                    <div className="form-group">
                      <label>Drip-feed 수량</label>
                      <input
                        type="number"
                        value={packageForm.drip_quantity}
                        onChange={(e) => setPackageForm({ ...packageForm, drip_quantity: e.target.value })}
                        placeholder="예: 400"
                        min="1"
                      />
                    </div>
                  </>
                )}
              </div>

              {/* 패키지 아이템 */}
              <div style={{ marginTop: '24px', paddingTop: '24px', borderTop: '2px solid #e5e7eb' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h4 style={{ fontSize: '16px', fontWeight: '600' }}>패키지 아이템</h4>
                  <button type="button" onClick={addPackageItem} className="btn-primary" style={{ padding: '8px 16px' }}>
                    <Plus size={16} /> 아이템 추가
                  </button>
                </div>

                {packageForm.items.map((item, index) => (
                  <div key={index} style={{
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                    padding: '16px',
                    marginBottom: '12px',
                    backgroundColor: '#f9fafb'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <strong>단계 {item.step}</strong>
                      <button
                        type="button"
                        onClick={() => removePackageItem(index)}
                        style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer' }}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>

                    <div className="form-group">
                      <label>세부서비스 *</label>
                      <select
                        value={item.variant_id || ''}
                        onChange={(e) => updatePackageItem(index, 'variant_id', e.target.value ? parseInt(e.target.value) : null)}
                        required
                      >
                        <option value="">선택하세요</option>
                        {variants.filter(v => v.is_active).map(variant => {
                          const product =
                            products.find(p => p.product_id === variant.product_id)
                          const productLabel = product ? ` (${product.name})` : ''
                          return (
                            <option key={variant.variant_id} value={variant.variant_id}>
                              {variant.name}
                              {productLabel}
                            </option>
                          )
                        })}
                      </select>
                    </div>

                    <div className="form-row">
                      <div className="form-group">
                        <label>수량</label>
                        <input
                          type="number"
                          value={item.quantity || ''}
                          onChange={(e) => updatePackageItem(index, 'quantity', e.target.value ? parseInt(e.target.value) : null)}
                        />
                      </div>
                      <div className="form-group">
                        <label>간격 값</label>
                        <input
                          type="number"
                          value={item.term_value || ''}
                          onChange={(e) => updatePackageItem(index, 'term_value', e.target.value ? parseInt(e.target.value) : null)}
                        />
                      </div>
                      <div className="form-group">
                        <label>간격 단위</label>
                        <select
                          value={item.term_unit || 'day'}
                          onChange={(e) => updatePackageItem(index, 'term_unit', e.target.value)}
                        >
                          <option value="day">일</option>
                          <option value="week">주</option>
                          <option value="month">월</option>
                        </select>
                      </div>
                    </div>

                    <div className="form-row">
                      <div className="form-group">
                        <label>반복 횟수</label>
                        <input
                          type="number"
                          value={item.repeat_count || ''}
                          onChange={(e) => updatePackageItem(index, 'repeat_count', e.target.value ? parseInt(e.target.value) : null)}
                        />
                      </div>
                      <div className="form-group">
                        <label>반복 간격 값</label>
                        <input
                          type="number"
                          value={item.repeat_term_value || ''}
                          onChange={(e) => updatePackageItem(index, 'repeat_term_value', e.target.value ? parseInt(e.target.value) : null)}
                        />
                      </div>
                      <div className="form-group">
                        <label>반복 간격 단위</label>
                        <select
                          value={item.repeat_term_unit || 'day'}
                          onChange={(e) => updatePackageItem(index, 'repeat_term_unit', e.target.value)}
                        >
                          <option value="day">일</option>
                          <option value="week">주</option>
                          <option value="month">월</option>
                        </select>
                      </div>
                    </div>
                  </div>
                ))}

                {packageForm.items.length === 0 && (
                  <p style={{ color: '#6b7280', textAlign: 'center', padding: '24px' }}>
                    패키지 아이템이 없습니다. "아이템 추가" 버튼을 클릭하여 추가하세요.
                  </p>
                )}
              </div>

              <div className="modal-actions">
                <button type="button" onClick={() => setShowPackageModal(false)}>
                  취소
                </button>
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? '저장 중...' : '저장'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default AdminServiceManagement









