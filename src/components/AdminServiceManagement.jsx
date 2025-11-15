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
  ChevronRight
} from 'lucide-react'
import './AdminServiceManagement.css'

const AdminServiceManagement = ({ adminFetch }) => {
  const [categories, setCategories] = useState([])
  const [products, setProducts] = useState([])
  const [variants, setVariants] = useState([])
  const [packages, setPackages] = useState([])
  const [selectedCategory, setSelectedCategory] = useState(null)
  const [selectedProduct, setSelectedProduct] = useState(null)
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
    auto_tag: false,
    is_package: false,
    // 세부서비스 정보
    variant_name: '',
    variant_price: '',
    variant_min_quantity: '',
    variant_max_quantity: '',
    variant_delivery_time: '',
    variant_is_active: true,
    variant_meta_json: {},
    variant_api_endpoint: ''
  })
  const [variantForm, setVariantForm] = useState({
    product_id: null,
    name: '',
    price: '',
    min_quantity: '',
    max_quantity: '',
    delivery_time_days: '',
    is_active: true,
    meta_json: {},
    api_endpoint: ''
  })
  const [packageForm, setPackageForm] = useState({
    category_id: null,
    name: '',
    description: '',
    items: []
  })

  // 데이터 로드
  useEffect(() => {
    loadCategories()
    loadProducts()
    loadVariants()
    loadPackages()
  }, [])

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

  // 카테고리 토글
  const toggleCategory = (categoryId) => {
    const newExpanded = new Set(expandedCategories)
    if (newExpanded.has(categoryId)) {
      newExpanded.delete(categoryId)
    } else {
      newExpanded.add(categoryId)
    }
    setExpandedCategories(newExpanded)
  }

  // 카테고리별 상품 필터링
  const getProductsByCategory = (categoryId) => {
    return products.filter(p => p.category_id === categoryId)
  }

  // 상품별 옵션 필터링
  const getVariantsByProduct = (productId) => {
    return variants.filter(v => v.product_id === productId)
  }

  // 카테고리 추가/수정
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

  // 상품 추가/수정 (세부서비스 정보 포함)
  const handleProductSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      // 1. 상품 먼저 생성/수정
      const productUrl = editingItem
        ? `/api/admin/products/${editingItem.product_id}`
        : `/api/admin/products`
      
      const productMethod = editingItem ? 'PUT' : 'POST'
      
      const productResponse = await adminFetch(productUrl, {
        method: productMethod,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category_id: parseInt(productForm.category_id),
          name: productForm.name,
          description: productForm.description,
          is_domestic: productForm.is_domestic,
          auto_tag: productForm.auto_tag
        })
      })

      if (!productResponse.ok) {
        const data = await productResponse.json()
        setError(data.error || '상품 저장 실패')
        return
      }

      const productData = await productResponse.json()
      const savedProductId = editingItem ? editingItem.product_id : productData.product?.product_id

      // 2. 세부서비스(옵션) 정보가 있으면 함께 생성
      if (productForm.variant_name && productForm.variant_price) {
        const variantResponse = await adminFetch('/api/admin/product-variants', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            product_id: savedProductId,
            name: productForm.variant_name,
            price: parseFloat(productForm.variant_price),
            min_quantity: productForm.variant_min_quantity ? parseInt(productForm.variant_min_quantity) : null,
            max_quantity: productForm.variant_max_quantity ? parseInt(productForm.variant_max_quantity) : null,
            delivery_time_days: productForm.variant_delivery_time ? parseInt(productForm.variant_delivery_time) : null,
            is_active: productForm.variant_is_active !== false,
            meta_json: productForm.variant_meta_json || {},
            api_endpoint: productForm.variant_api_endpoint || null
          })
        })

        if (!variantResponse.ok) {
          const variantData = await variantResponse.json()
          setError(variantData.error || '세부서비스 저장 실패')
          return
        }
      }

      await loadProducts()
      await loadVariants()
      setShowProductModal(false)
      setEditingItem(null)
      setProductForm({
        category_id: null,
        name: '',
        description: '',
        is_domestic: true,
        auto_tag: false,
        is_package: false,
        variant_name: '',
        variant_price: '',
        variant_min_quantity: '',
        variant_max_quantity: '',
        variant_delivery_time: '',
        variant_is_active: true,
        variant_meta_json: {},
        variant_api_endpoint: ''
      })
    } catch (err) {
      setError('상품 저장 중 오류 발생')
    } finally {
      setLoading(false)
    }
  }

  // 옵션 추가/수정
  const handleVariantSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const url = editingItem
        ? `/api/admin/product-variants/${editingItem.variant_id}`
        : `/api/admin/product-variants`
      
      const method = editingItem ? 'PUT' : 'POST'
      
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
          meta_json: variantForm.meta_json,
          api_endpoint: variantForm.api_endpoint || null
        })
      })

      if (response.ok) {
        await loadVariants()
        setShowVariantModal(false)
        setEditingItem(null)
        setVariantForm({
          product_id: null,
          name: '',
          price: '',
          min_quantity: '',
          max_quantity: '',
          delivery_time_days: '',
          is_active: true,
          meta_json: {},
          api_endpoint: ''
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
    if (!confirm('카테고리를 비활성화하시겠습니까?')) return

    try {
      const response = await adminFetch(`/api/admin/categories/${categoryId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        await loadCategories()
      }
    } catch (err) {
      console.error('카테고리 삭제 실패:', err)
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
        auto_tag: product.auto_tag || false,
        is_package: false
      })
    } else {
      setEditingItem(null)
        setProductForm({
          category_id: categoryId || null,
          name: '',
          description: '',
          is_domestic: true,
          auto_tag: false,
          is_package: false,
          variant_name: '',
          variant_price: '',
          variant_min_quantity: '',
          variant_max_quantity: '',
          variant_delivery_time: '',
          variant_is_active: true,
          variant_meta_json: {},
          variant_api_endpoint: ''
        })
    }
    setShowProductModal(true)
  }

  const openVariantModal = (variant = null, productId = null) => {
    if (variant) {
      setEditingItem(variant)
      setVariantForm({
        product_id: variant.product_id,
        name: variant.name,
        price: variant.price,
        min_quantity: variant.min_quantity || '',
        max_quantity: variant.max_quantity || '',
        delivery_time_days: variant.delivery_time_days || '',
        is_active: variant.is_active,
        meta_json: variant.meta_json || {},
        api_endpoint: variant.api_endpoint || ''
      })
    } else {
      setEditingItem(null)
      setVariantForm({
        product_id: productId || null,
        name: '',
        price: '',
        min_quantity: '',
        max_quantity: '',
        delivery_time_days: '',
        is_active: true,
        meta_json: {},
        api_endpoint: ''
      })
    }
    setShowVariantModal(true)
  }

  return (
    <div className="admin-service-management">
      <div className="service-header">
        <h2>서비스 관리</h2>
        <div className="header-actions">
          <button 
            className="btn-primary"
            onClick={() => openProductModal()}
          >
            <Plus size={16} /> 상품 추가
          </button>
          <button 
            className="btn-primary"
            onClick={() => openCategoryModal()}
          >
            <Plus size={16} /> 카테고리 추가
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div className="service-tree">
        {categories.map(category => {
          const categoryProducts = getProductsByCategory(category.category_id)
          const isExpanded = expandedCategories.has(category.category_id)

          return (
            <div key={category.category_id} className="category-item">
              <div 
                className="category-header"
                onClick={() => toggleCategory(category.category_id)}
              >
                {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                <Tag size={16} />
                <span className="category-name">{category.name}</span>
                {!category.is_active && <span className="inactive-badge">비활성</span>}
                <div className="category-actions">
                  <button
                    className="btn-icon"
                    onClick={(e) => {
                      e.stopPropagation()
                      openProductModal(null, category.category_id)
                    }}
                    title="상품 추가"
                  >
                    <Plus size={14} />
                  </button>
                  <button
                    className="btn-icon"
                    onClick={(e) => {
                      e.stopPropagation()
                      openCategoryModal(category)
                    }}
                    title="수정"
                  >
                    <Edit size={14} />
                  </button>
                  <button
                    className="btn-icon"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDeleteCategory(category.category_id)
                    }}
                    title="삭제"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {isExpanded && (
                <div className="category-content">
                  {categoryProducts.length === 0 ? (
                    <div className="empty-state">
                      상품이 없습니다. 상품을 추가해주세요.
                    </div>
                  ) : (
                    categoryProducts.map(product => {
                      const productVariants = getVariantsByProduct(product.product_id)

                      return (
                        <div key={product.product_id} className="product-item">
                          <div className="product-header">
                            <Layers size={14} />
                            <span className="product-name">{product.name}</span>
                            <div className="product-actions">
                              <button
                                className="btn-icon"
                                onClick={() => openVariantModal(null, product.product_id)}
                                title="옵션 추가"
                              >
                                <Plus size={14} />
                              </button>
                              <button
                                className="btn-icon"
                                onClick={() => openProductModal(product)}
                                title="수정"
                              >
                                <Edit size={14} />
                              </button>
                              <button
                                className="btn-icon"
                                onClick={() => handleDeleteProduct(product.product_id)}
                                title="삭제"
                              >
                                <Trash2 size={14} />
                              </button>
                            </div>
                          </div>

                          <div className="variants-list">
                            {productVariants.length === 0 ? (
                              <div className="empty-state-small">
                                옵션이 없습니다.
                              </div>
                            ) : (
                              productVariants.map(variant => (
                                <div key={variant.variant_id} className="variant-item">
                                  <span className="variant-name">{variant.name}</span>
                                  <span className="variant-price">{parseFloat(variant.price).toLocaleString()}원</span>
                                  <div className="variant-actions">
                                    <button
                                      className="btn-icon-small"
                                      onClick={() => openVariantModal(variant)}
                                      title="수정"
                                    >
                                      <Edit size={12} />
                                    </button>
                                    <button
                                      className="btn-icon-small"
                                      onClick={() => handleDeleteVariant(variant.variant_id)}
                                      title="삭제"
                                    >
                                      <Trash2 size={12} />
                                    </button>
                                  </div>
                                </div>
                              ))
                            )}
                          </div>
                        </div>
                      )
                    })
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* 전체 상품 목록 섹션 */}
      <div className="all-products-section">
        <div className="section-header">
          <h3>전체 세부서비스 목록</h3>
          <span className="product-count">총 {variants.length}개 세부서비스</span>
        </div>
        <div className="all-products-grid">
          {variants.length === 0 ? (
            <div className="empty-state">
              등록된 세부서비스가 없습니다. 상품을 추가해주세요.
            </div>
          ) : (
            variants.map(variant => {
              const product = products.find(p => p.product_id === variant.product_id)
              const category = product ? categories.find(c => c.category_id === product.category_id) : null
              
              return (
                <div key={variant.variant_id} className="product-card">
                  <div className="product-card-header">
                    <div className="product-card-title">
                      <Layers size={16} />
                      <span className="product-name">{variant.name}</span>
                      {category && (
                        <span className="category-badge">{category.name}</span>
                      )}
                      {product && (
                        <span className="product-badge">{product.name}</span>
                      )}
                    </div>
                    <div className="product-card-actions">
                      <button
                        className="btn-icon"
                        onClick={() => openVariantModal(variant)}
                        title="수정"
                      >
                        <Edit size={14} />
                      </button>
                      <button
                        className="btn-icon"
                        onClick={() => handleDeleteVariant(variant.variant_id)}
                        title="삭제"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                  <div className="variant-details">
                    <div className="detail-row">
                      <span className="detail-label">가격:</span>
                      <span className="detail-value price">{parseFloat(variant.price).toLocaleString()}원</span>
                    </div>
                    {variant.min_quantity && (
                      <div className="detail-row">
                        <span className="detail-label">최소 수량:</span>
                        <span className="detail-value">{variant.min_quantity.toLocaleString()}</span>
                      </div>
                    )}
                    {variant.max_quantity && (
                      <div className="detail-row">
                        <span className="detail-label">최대 수량:</span>
                        <span className="detail-value">{variant.max_quantity.toLocaleString()}</span>
                      </div>
                    )}
                    {variant.delivery_time_days && (
                      <div className="detail-row">
                        <span className="detail-label">배송 시간:</span>
                        <span className="detail-value">{variant.delivery_time_days}일</span>
                      </div>
                    )}
                    <div className="detail-row">
                      <span className="detail-label">상태:</span>
                      <span className={`detail-value status ${variant.is_active ? 'active' : 'inactive'}`}>
                        {variant.is_active ? '활성' : '비활성'}
                      </span>
                    </div>
                    {variant.api_endpoint && (
                      <div className="detail-row">
                        <span className="detail-label">API:</span>
                        <span className="detail-value api-endpoint">{variant.api_endpoint}</span>
                      </div>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>
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
                    checked={productForm.auto_tag}
                    onChange={(e) => setProductForm({ ...productForm, auto_tag: e.target.checked })}
                  />
                  자동 태그
                </label>
              </div>

              {/* 세부서비스 정보 섹션 */}
              <div style={{ marginTop: '24px', paddingTop: '24px', borderTop: '2px solid #e5e7eb' }}>
                <h4 style={{ marginBottom: '16px', fontSize: '16px', fontWeight: '600' }}>세부서비스 정보</h4>
                
                <div className="form-group">
                  <label>세부서비스 이름 *</label>
                  <input
                    type="text"
                    value={productForm.variant_name}
                    onChange={(e) => setProductForm({ ...productForm, variant_name: e.target.value })}
                    placeholder="예: 인스타그램 팔로워 1000명"
                    required
                  />
                </div>
                
                <div className="form-row">
                  <div className="form-group">
                    <label>가격 *</label>
                    <input
                      type="number"
                      step="0.01"
                      value={productForm.variant_price}
                      onChange={(e) => setProductForm({ ...productForm, variant_price: e.target.value })}
                      placeholder="0.00"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>배송 시간 (일)</label>
                    <input
                      type="number"
                      value={productForm.variant_delivery_time}
                      onChange={(e) => setProductForm({ ...productForm, variant_delivery_time: e.target.value })}
                      placeholder="예: 1"
                    />
                  </div>
                </div>
                
                <div className="form-row">
                  <div className="form-group">
                    <label>최소 수량</label>
                    <input
                      type="number"
                      value={productForm.variant_min_quantity}
                      onChange={(e) => setProductForm({ ...productForm, variant_min_quantity: e.target.value })}
                      placeholder="예: 100"
                    />
                  </div>
                  <div className="form-group">
                    <label>최대 수량</label>
                    <input
                      type="number"
                      value={productForm.variant_max_quantity}
                      onChange={(e) => setProductForm({ ...productForm, variant_max_quantity: e.target.value })}
                      placeholder="예: 10000"
                    />
                  </div>
                </div>
                
                <div className="form-group">
                  <label>API 엔드포인트</label>
                  <input
                    type="text"
                    value={productForm.variant_api_endpoint}
                    onChange={(e) => setProductForm({ ...productForm, variant_api_endpoint: e.target.value })}
                    placeholder="SMM Panel API 엔드포인트"
                  />
                </div>
                
                <div className="form-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={productForm.variant_is_active}
                      onChange={(e) => setProductForm({ ...productForm, variant_is_active: e.target.checked })}
                    />
                    세부서비스 활성화
                  </label>
                </div>
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

      {/* 옵션 모달 */}
      {showVariantModal && (
        <div className="modal-overlay" onClick={() => setShowVariantModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingItem ? '옵션 수정' : '옵션 추가'}</h3>
              <button className="btn-icon" onClick={() => setShowVariantModal(false)}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleVariantSubmit}>
              <div className="form-group">
                <label>상품 *</label>
                <select
                  value={variantForm.product_id || ''}
                  onChange={(e) => setVariantForm({ ...variantForm, product_id: e.target.value })}
                  required
                >
                  <option value="">선택하세요</option>
                  {products.map(prod => (
                    <option key={prod.product_id} value={prod.product_id}>
                      {prod.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>옵션 이름 *</label>
                <input
                  type="text"
                  value={variantForm.name}
                  onChange={(e) => setVariantForm({ ...variantForm, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>가격 *</label>
                  <input
                    type="number"
                    step="0.01"
                    value={variantForm.price}
                    onChange={(e) => setVariantForm({ ...variantForm, price: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>배송 시간 (일)</label>
                  <input
                    type="number"
                    value={variantForm.delivery_time_days}
                    onChange={(e) => setVariantForm({ ...variantForm, delivery_time_days: e.target.value })}
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>최소 수량</label>
                  <input
                    type="number"
                    value={variantForm.min_quantity}
                    onChange={(e) => setVariantForm({ ...variantForm, min_quantity: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>최대 수량</label>
                  <input
                    type="number"
                    value={variantForm.max_quantity}
                    onChange={(e) => setVariantForm({ ...variantForm, max_quantity: e.target.value })}
                  />
                </div>
              </div>
              <div className="form-group">
                <label>API 엔드포인트</label>
                <input
                  type="url"
                  value={variantForm.api_endpoint}
                  onChange={(e) => setVariantForm({ ...variantForm, api_endpoint: e.target.value })}
                />
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
    </div>
  )
}

export default AdminServiceManagement

