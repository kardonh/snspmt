import React, { useState, useEffect } from 'react';
import { Search, RefreshCw, Plus, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import api from '@/services/api';
import CategoryFormModal from './service-management/CategoryFormModal';
import ProductFormModal from './service-management/ProductFormModal';
import VariantFormModal from './service-management/VariantFormModal';
import PackageFormModal from './service-management/PackageFormModal';
import ServiceTreeView from './service-management/ServiceTreeView';
import PackageList from './service-management/PackageList';

function AdminServices() {
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [variants, setVariants] = useState([]);
  const [packages, setPackages] = useState([]);
  
  const [expandedCategories, setExpandedCategories] = useState([]);
  const [expandedProducts, setExpandedProducts] = useState([]);
  const [variantSearchTerm, setVariantSearchTerm] = useState('');
  
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [showProductModal, setShowProductModal] = useState(false);
  const [showVariantModal, setShowVariantModal] = useState(false);
  const [showPackageModal, setShowPackageModal] = useState(false);
  
  const [editingItem, setEditingItem] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const [categoryForm, setCategoryForm] = useState({ 
    name: '', slug: '', image_url: '', is_active: true 
  });
  const [productForm, setProductForm] = useState({ 
    category_id: null, name: '', description: '', is_domestic: true, is_auto: false, auto_tag: false, is_package: false 
  });
  const [variantForm, setVariantForm] = useState({
    category_id: null, product_id: null, name: '', price: '', description: '', 
    min_quantity: '', max_quantity: '', delivery_time_days: '', time: '', 
    smm_service_id: '', api_endpoint: '',
    requires_comments: false, requires_custom_fields: false, custom_fields_config: {},
    drip_feed: false, runs: '', interval: '', drip_quantity: '', is_active: true, meta_json: {}
  });
  const [packageForm, setPackageForm] = useState({
    product_id: null, name: '', description: '', price: '', 
    min_quantity: '', max_quantity: '', time: '', smmkings_id: '',
    drip_feed: false, runs: '', interval: '', drip_quantity: '', items: []
  });
  const [variantSearchTerms, setVariantSearchTerms] = useState({});

  
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const refreshData = async () => {
    alert('변경 완료!')
    window.location.reload();
  };

  useEffect(() => {
    loadData();
    loadSmmEndpoint();
  }, [refreshTrigger]);

  const loadData = async () => {
    try {
      await Promise.all([loadCategories(), loadProducts(), loadVariants(), loadPackages()]);
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  };

  const loadCategories = async () => {
    try {
      const response = await api.get('/admin/categories?include_inactive=true');
      setCategories(response.data.categories || []);
    } catch (err) {
      console.error('카테고리 로드 실패:', err);
    }
  };

  const loadProducts = async () => {
    try {
      const response = await api.get('/admin/products');
      setProducts(response.data.products || []);
    } catch (err) {
      console.error('상품 로드 실패:', err);
    }
  };

  const loadVariants = async () => {
    try {
      const response = await api.get('/admin/product-variants');
      setVariants(response.data.variants || []);
    } catch (err) {
      console.error('옵션 로드 실패:', err);
    }
  };

  const loadPackages = async () => {
    try {
      const response = await api.get('/admin/packages');
      setPackages(response.data.packages || []);
    } catch (err) {
      console.error('패키지 로드 실패:', err);
    }
  };

  const loadSmmEndpoint = async () => {
    try {
      const response = await api.get('/admin/config');
      if (response.data.smm_api_endpoint && !variantForm.api_endpoint) {
        setVariantForm(prev => ({ ...prev, api_endpoint: response.data.smm_api_endpoint }));
      }
    } catch (err) {
      console.error('SMM API 엔드포인트 로드 실패:', err);
    }
  };

  const toggleCategory = (id) => {
    setExpandedCategories(prev => 
      prev.includes(id) ? prev.filter(cid => cid !== id) : [...prev, id]
    );
  };

  const toggleProduct = (id) => {
    setExpandedProducts(prev => 
      prev.includes(id) ? prev.filter(pid => pid !== id) : [...prev, id]
    );
  };

  // Helper functions
  const getProductsBySelectedCategory = () => {
    if (!variantForm.category_id) return [];
    return products.filter(p => p.category_id === parseInt(variantForm.category_id));
  };

  const filteredVariants = variantSearchTerm ? variants.filter(v => {
    const searchLower = variantSearchTerm.toLowerCase();
    return (
      v.name?.toLowerCase().includes(searchLower) ||
      v.description?.toLowerCase().includes(searchLower) ||
      v.price?.toString().includes(searchLower)
    );
  }) : null;

  useEffect(() => {
    if (variantSearchTerm && filteredVariants) {
      const relevantProducts = new Set();
      const relevantCategories = new Set();
      
      filteredVariants.forEach(variant => {
        const product = products.find(p => p.product_id === variant.product_id);
        if (product) {
          relevantProducts.add(product.product_id);
          relevantCategories.add(product.category_id);
        }
      });
      
      setExpandedProducts(Array.from(relevantProducts));
      setExpandedCategories(Array.from(relevantCategories));
    }
  }, [variantSearchTerm, filteredVariants, products]);

  // Category handlers
  const openCategoryModal = (category = null) => {
    if (category) {
      setEditingItem(category);
      setCategoryForm({ 
        name: category.name, 
        slug: category.slug || '', 
        image_url: category.image_url || '', 
        is_active: category.is_active 
      });
    } else {
      setEditingItem(null);
      setCategoryForm({ name: '', slug: '', image_url: '', is_active: true });
    }
    setShowCategoryModal(true);
  };

  const handleSaveCategory = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (editingItem) {
        await api.put(`/admin/categories/${editingItem.category_id}`, categoryForm);
      } else {
        await api.post('/admin/categories', categoryForm);
      }
      await loadCategories();
      setShowCategoryModal(false);
      setEditingItem(null);
      setCategoryForm({ name: '', slug: '', image_url: '', is_active: true });
      
    } catch (err) {
      const errorMsg = err.response?.data?.error || '카테고리 저장 실패';
      setError(errorMsg);
      alert(errorMsg);
    } finally {
      setLoading(false);
      refreshData();
    }
  };

  const handleDeleteCategory = async (id) => {
    if (!window.confirm('카테고리를 삭제하시겠습니까?\n\n연결된 상품이나 패키지도 함께 삭제될 수 있습니다.')) return;
    
    try {
      const response = await api.delete(`/admin/categories/${id}`);
      alert(response.data.message || '카테고리가 삭제되었습니다.');
      await Promise.all([loadCategories(), loadProducts(), loadVariants(), loadPackages()]);
    } catch (err) {
      console.error('카테고리 삭제 실패:', err);
      alert(err.response?.data?.error || '카테고리 삭제 중 오류가 발생했습니다.');
    }
    finally {
      refreshData();
    }
  };

  // Product handlers
  const openProductModal = (product = null, category = null) => {
    if (product) {
      setEditingItem(product);
      setProductForm({
        category_id: product.category_id,
        name: product.name,
        description: product.description || '',
        is_domestic: product.is_domestic || false,
        is_auto: product.is_auto || false,
        auto_tag: product.auto_tag || false
      });
    } else {
      setEditingItem(null);
      setProductForm({
        category_id: category?.category_id || null,
        name: '',
        description: '',
        is_domestic: false,
        is_auto: false,
        auto_tag: false
      });
    }
    setShowProductModal(true);
  };

  const handleSaveProduct = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload = {
        category_id: parseInt(productForm.category_id),
        name: productForm.name,
        description: productForm.description,
        is_domestic: productForm.is_domestic,
        is_auto: productForm.is_auto,
        auto_tag: productForm.auto_tag
      };

      if (editingItem) {
        await api.put(`/admin/products/${editingItem.product_id}`, payload);
      } else {
        await api.post('/admin/products', payload);
      }
      
      await loadProducts();
      setShowProductModal(false);
      setEditingItem(null);
      setProductForm({
        category_id: null,
        name: '',
        description: '',
        is_domestic: true,
        is_auto: false,
        auto_tag: false,
        is_package: false
      });
    } catch (err) {
      const errorMsg = err.response?.data?.error || '상품 저장 실패';
      setError(errorMsg);
      alert(errorMsg);
    } finally {
      setLoading(false);
      refreshData();
    }
  };

  const handleDeleteProduct = async (id) => {
    if (!window.confirm('상품을 삭제하시겠습니까?')) return;
    
    try {
      await api.delete(`/admin/products/${id}`);
      await Promise.all([loadProducts(), loadVariants()]);
    } catch (err) {
      console.error('상품 삭제 실패:', err);
      alert(err.response?.data?.error || '상품 삭제 중 오류가 발생했습니다.');
    }
    finally {
      refreshData();
    }
  };

  // Variant handlers
  const openVariantModal = (variant = null, product = null, categoryId = null) => {
    if (variant) {
      setEditingItem(variant);
      const productData = products.find(p => p.product_id === variant.product_id);
      const catId = productData ? productData.category_id : null;
      
      const meta = variant.meta_json || {};
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
        requires_comments: meta.requires_comments || false,
        requires_custom_fields: meta.requires_custom_fields || false,
        custom_fields_config: meta.custom_fields_config || {}
      });
    } else {
      setEditingItem(null);
      setVariantForm({
        category_id: categoryId || null,
        product_id: product?.product_id || null,
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
      });
    }
    setShowVariantModal(true);
  };

  const handleSaveVariant = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // meta_json 구성
      const metaJson = {
        ...(variantForm.meta_json || {}),
        description: variantForm.description || null,
        time: variantForm.time || null,
        smm_service_id: variantForm.smm_service_id ? parseInt(variantForm.smm_service_id) : null,
        id: variantForm.smm_service_id ? parseInt(variantForm.smm_service_id) : null,
        drip_feed: variantForm.drip_feed || false,
        runs: variantForm.runs ? parseInt(variantForm.runs) : null,
        interval: variantForm.interval ? parseInt(variantForm.interval) : null,
        drip_quantity: variantForm.drip_quantity ? parseInt(variantForm.drip_quantity) : null,
        requires_comments: variantForm.requires_comments || false,
        requires_custom_fields: variantForm.requires_custom_fields || false,
        custom_fields_config: variantForm.custom_fields_config || {}
      };
      
      // null 값 제거
      Object.keys(metaJson).forEach(key => {
        if (metaJson[key] === null || metaJson[key] === '') {
          delete metaJson[key];
        }
      });

      const payload = {
        product_id: parseInt(variantForm.product_id),
        name: variantForm.name,
        price: parseFloat(variantForm.price),
        min_quantity: variantForm.min_quantity ? parseInt(variantForm.min_quantity) : null,
        max_quantity: variantForm.max_quantity ? parseInt(variantForm.max_quantity) : null,
        delivery_time_days: variantForm.delivery_time_days ? parseInt(variantForm.delivery_time_days) : null,
        is_active: variantForm.is_active,
        meta_json: metaJson,
        api_endpoint: variantForm.api_endpoint || null
      };

      if (editingItem) {
        await api.put(`/admin/product-variants/${editingItem.variant_id}`, payload);
      } else {
        await api.post('/admin/product-variants', payload);
      }

      await loadVariants();
      setShowVariantModal(false);
      setEditingItem(null);
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
      });
    } catch (err) {
      const errorMsg = err.response?.data?.error || '옵션 저장 실패';
      setError(errorMsg);
      alert(errorMsg);
    } finally {
      setLoading(false);
      refreshData();
    }
  };

  const handleDeleteVariant = async (id) => {
    if (!window.confirm('옵션을 삭제하시겠습니까?')) return;
    
    try {
      await api.delete(`/admin/product-variants/${id}`);
      await loadVariants();
    } catch (err) {
      console.error('옵션 삭제 실패:', err);
      alert(err.response?.data?.error || '세부서비스 삭제 중 오류가 발생했습니다.');
    }
    finally {
      refreshData();
    }
  };

  // Package handlers
  const openPackageModal = (pkg = null, productId = null) => {
    if (pkg) {
      setEditingItem(pkg);
      const meta = pkg.meta_json || {};
      const product = products.find(p => p.category_id === pkg.category_id);
      setPackageForm({
        product_id: product ? product.product_id : null,
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
      });
    } else {
      setEditingItem(null);
      setPackageForm({
        product_id: productId || null,
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
      });
    }
    setVariantSearchTerms({});
    setShowPackageModal(true);
  };

  const handleSavePackage = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // meta_json 구성
      const metaJson = {
        price: packageForm.price ? parseFloat(packageForm.price) : null,
        min: packageForm.min_quantity ? parseInt(packageForm.min_quantity) : null,
        min_quantity: packageForm.min_quantity ? parseInt(packageForm.min_quantity) : null,
        max: packageForm.max_quantity ? parseInt(packageForm.max_quantity) : null,
        max_quantity: packageForm.max_quantity ? parseInt(packageForm.max_quantity) : null,
        time: packageForm.time || null,
        smmkings_id: packageForm.smmkings_id ? parseInt(packageForm.smmkings_id) : null,
        id: packageForm.smmkings_id ? parseInt(packageForm.smmkings_id) : null,
        drip_feed: packageForm.drip_feed || false,
        runs: packageForm.runs ? parseInt(packageForm.runs) : null,
        interval: packageForm.interval ? parseInt(packageForm.interval) : null,
        drip_quantity: packageForm.drip_quantity ? parseInt(packageForm.drip_quantity) : null
      };
      
      // null 값 제거
      Object.keys(metaJson).forEach(key => {
        if (metaJson[key] === null || metaJson[key] === '') {
          delete metaJson[key];
        }
      });

      // product_id로 category_id 찾기
      const selectedProduct = products.find(p => p.product_id === parseInt(packageForm.product_id));
      if (!selectedProduct && packageForm.product_id) {
        throw new Error('선택한 상품을 찾을 수 없습니다.');
      }
      
      const payload = {
        product_id: packageForm.product_id ? parseInt(packageForm.product_id) : null,
        category_id: selectedProduct ? selectedProduct.category_id : null,
        name: packageForm.name,
        description: packageForm.description,
        meta_json: Object.keys(metaJson).length > 0 ? metaJson : null,
        items: packageForm.items
      };

      if (editingItem) {
        await api.put(`/admin/packages/${editingItem.package_id}`, payload);
      } else {
        await api.post('/admin/packages', payload);
      }

      await loadPackages();
      setShowPackageModal(false);
      setEditingItem(null);
      setPackageForm({
        product_id: null,
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
      });
      setVariantSearchTerms({});
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.message || '패키지 저장 중 오류 발생';
      setError(errorMsg);
      alert(errorMsg);
    } finally {
      setLoading(false);
      refreshData();
    }
  };

  const handleDeletePackage = async (id) => {
    if (!window.confirm('패키지를 삭제하시겠습니까?')) return;
    
    try {
      await api.delete(`/admin/packages/${id}`);
      await loadPackages();
    } catch (err) {
      console.error('패키지 삭제 실패:', err);
      alert(err.response?.data?.error || '패키지 삭제 중 오류가 발생했습니다.');
    }
    finally {
      refreshData();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">서비스 관리</h2>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadData}>
            <RefreshCw className="h-4 w-4 mr-2" /> 새로고침
          </Button>
          <Button onClick={() => openCategoryModal()}>
            <Plus className="h-4 w-4 mr-2" /> 카테고리 추가
          </Button>
        </div>
      </div>

      {/* Variant Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          type="text"
          placeholder="세부서비스 검색... (이름, 가격, 설명)"
          value={variantSearchTerm}
          onChange={(e) => setVariantSearchTerm(e.target.value)}
          className="pl-9 pr-8"
        />
        {variantSearchTerm && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
            onClick={() => setVariantSearchTerm('')}
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      {variantSearchTerm && filteredVariants && (
        <p className="text-sm text-blue-600">
          {filteredVariants.length}개 발견. 일치하는 세부서비스를 자동으로 표시합니다.
        </p>
      )}

      {/* Service Tree */}
      <ServiceTreeView
        categories={categories}
        products={products}
        variants={variants}
        expandedCategories={expandedCategories}
        expandedProducts={expandedProducts}
        onToggleCategory={toggleCategory}
        onToggleProduct={toggleProduct}
        onEditCategory={openCategoryModal}
        onEditProduct={openProductModal}
        onEditVariant={openVariantModal}
        onDeleteCategory={handleDeleteCategory}
        onDeleteProduct={handleDeleteProduct}
        onDeleteVariant={handleDeleteVariant}
        onAddProduct={openProductModal}
        onAddVariant={openVariantModal}
        searchTerm={variantSearchTerm}
        filteredVariants={filteredVariants}
      />

      {/* Package Section */}
      <div className="pt-6 border-t">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-bold">패키지 관리</h3>
          <Button onClick={() => openPackageModal()}>
            <Plus className="h-4 w-4 mr-2" /> 패키지 추가
          </Button>
        </div>
        <PackageList
          packages={packages}
          categories={categories}
          onEdit={openPackageModal}
          onDelete={handleDeletePackage}
        />
      </div>

      {/* Modals */}
      <CategoryFormModal
        open={showCategoryModal}
        onOpenChange={setShowCategoryModal}
        form={categoryForm}
        onFormChange={setCategoryForm}
        onSubmit={handleSaveCategory}
        isEditing={!!editingItem}
      />

      <ProductFormModal
        open={showProductModal}
        onOpenChange={setShowProductModal}
        form={productForm}
        onFormChange={setProductForm}
        categories={categories}
        onSubmit={handleSaveProduct}
        isEditing={!!editingItem}
      />

      <VariantFormModal
        open={showVariantModal}
        onOpenChange={setShowVariantModal}
        form={variantForm}
        onFormChange={setVariantForm}
        products={products}
        categories={categories}
        onSubmit={handleSaveVariant}
        isEditing={!!editingItem}
      />

      <PackageFormModal
        open={showPackageModal}
        onOpenChange={(open) => {
          setShowPackageModal(open);
          if (!open) setVariantSearchTerms({});
        }}
        packageForm={packageForm}
        onFormChange={setPackageForm}
        categories={categories}
        variants={variants}
        products={products}
        variantSearchTerms={variantSearchTerms}
        onSearchTermChange={(index, term) => 
          setVariantSearchTerms({ ...variantSearchTerms, [index]: term })
        }
        onSubmit={handleSavePackage}
        editingItem={editingItem}
      />
    </div>
  );
}

export default AdminServices;
