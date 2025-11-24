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
  const [categoryForm, setCategoryForm] = useState({ 
    name: '', slug: '', image_url: '', is_active: true 
  });
  const [productForm, setProductForm] = useState({ 
    category_id: null, name: '', description: '', is_domestic: false, is_auto: false, auto_tag: false 
  });
  const [variantForm, setVariantForm] = useState({
    category_id: null, product_id: null, name: '', price: '', description: '', 
    min_quantity: '', max_quantity: '', delivery_time_days: '', time: '', 
    smm_service_id: '', smmkings_id: '', api_endpoint: '',
    requires_comments: false, requires_custom_fields: false, custom_fields_config: {},
    drip_feed: false, runs: '', interval: '', drip_quantity: '', is_active: true
  });
  const [packageForm, setPackageForm] = useState({
    category_id: null, name: '', description: '', price: '', 
    min_quantity: '', max_quantity: '', time: '', smmkings_id: '',
    drip_feed: false, runs: '', interval: '', drip_quantity: '', items: []
  });
  const [variantSearchTerms, setVariantSearchTerms] = useState({});

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [catRes, prodRes, varRes, pkgRes] = await Promise.all([
        api.get('/admin/categories'),
        api.get('/admin/products'),
        api.get('/admin/product-variants'),
        api.get('/admin/packages')
      ]);
      setCategories(catRes.data.categories || []);
      setProducts(prodRes.data.products || []);
      setVariants(varRes.data.variants || []);
      setPackages(pkgRes.data.packages || []);
    } catch (error) {
      console.error('Failed to load data:', error);
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
    try {
      if (editingItem) {
        await api.put(`/admin/categories/${editingItem.category_id}`, categoryForm);
      } else {
        await api.post('/admin/categories', categoryForm);
      }
      await loadData();
      setShowCategoryModal(false);
      setEditingItem(null);
      setCategoryForm({ name: '', is_active: true });
    } catch (error) {
      alert('카테고리 저장 실패');
    }
  };

  const handleDeleteCategory = async (id) => {
    if (!window.confirm('정말 삭제하시겠습니까?')) return;
    try {
      await api.delete(`/admin/categories/${id}`);
      await loadData();
    } catch (error) {
      alert('카테고리 삭제 실패');
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
    try {
      if (editingItem) {
        await api.put(`/admin/products/${editingItem.product_id}`, productForm);
      } else {
        await api.post('/admin/products', productForm);
      }
      await loadData();
      setShowProductModal(false);
      setEditingItem(null);
      setProductForm({ category_id: null, name: '', is_domestic: false, is_auto: false, auto_tag: false });
    } catch (error) {
      alert('상품 저장 실패');
    }
  };

  const handleDeleteProduct = async (id) => {
    if (!window.confirm('정말 삭제하시겠습니까?')) return;
    try {
      await api.delete(`/admin/products/${id}`);
      await loadData();
    } catch (error) {
      alert('상품 삭제 실패');
    }
  };

  // Variant handlers
  const openVariantModal = (variant = null, product = null) => {
    if (variant) {
      setEditingItem(variant);
      const meta = variant.meta_json || {};
      const productData = products.find(p => p.product_id === variant.product_id);
      setVariantForm({
        category_id: productData?.category_id || null,
        product_id: variant.product_id,
        name: variant.name,
        price: meta.price || variant.price || '',
        description: variant.description || '',
        min_quantity: meta.min || meta.min_quantity || '',
        max_quantity: meta.max || meta.max_quantity || '',
        delivery_time_days: meta.delivery_time_days || '',
        time: meta.time || '',
        smm_service_id: meta.smm_service_id || meta.smmkings_id || meta.id || '',
        smmkings_id: meta.smmkings_id || meta.id || '',
        api_endpoint: meta.api_endpoint || '',
        requires_comments: meta.requires_comments || false,
        requires_custom_fields: meta.requires_custom_fields || false,
        custom_fields_config: meta.custom_fields_config || {},
        drip_feed: meta.drip_feed || false,
        runs: meta.runs || '',
        interval: meta.interval || '',
        drip_quantity: meta.drip_quantity || '',
        is_active: variant.is_active
      });
    } else {
      setEditingItem(null);
      setVariantForm({
        category_id: product ? products.find(p => p.product_id === product.product_id)?.category_id || null : null,
        product_id: product?.product_id || null,
        name: '',
        price: '',
        description: '',
        min_quantity: '',
        max_quantity: '',
        delivery_time_days: '',
        time: '',
        smm_service_id: '',
        smmkings_id: '',
        api_endpoint: '',
        requires_comments: false,
        requires_custom_fields: false,
        custom_fields_config: {},
        drip_feed: false,
        runs: '',
        interval: '',
        drip_quantity: '',
        is_active: true
      });
    }
    setShowVariantModal(true);
  };

  const handleSaveVariant = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        product_id: variantForm.product_id,
        name: variantForm.name,
        description: variantForm.description,
        is_active: variantForm.is_active,
        meta_json: {
          price: parseFloat(variantForm.price) || 0,
          min: parseInt(variantForm.min_quantity) || null,
          max: parseInt(variantForm.max_quantity) || null,
          min_quantity: parseInt(variantForm.min_quantity) || null,
          max_quantity: parseInt(variantForm.max_quantity) || null,
          delivery_time_days: parseInt(variantForm.delivery_time_days) || null,
          time: variantForm.time || null,
          smm_service_id: variantForm.smm_service_id || variantForm.smmkings_id || null,
          smmkings_id: variantForm.smmkings_id || variantForm.smm_service_id || null,
          id: variantForm.smmkings_id || variantForm.smm_service_id || null,
          api_endpoint: variantForm.api_endpoint || null,
          requires_comments: variantForm.requires_comments || false,
          requires_custom_fields: variantForm.requires_custom_fields || false,
          custom_fields_config: variantForm.custom_fields_config || {},
          drip_feed: variantForm.drip_feed || false,
          runs: variantForm.drip_feed ? parseInt(variantForm.runs) || null : null,
          interval: variantForm.drip_feed ? parseInt(variantForm.interval) || null : null,
          drip_quantity: variantForm.drip_feed ? parseInt(variantForm.drip_quantity) || null : null
        }
      };

      if (editingItem) {
        await api.put(`/admin/product-variants/${editingItem.variant_id}`, payload);
      } else {
        await api.post('/admin/product-variants', payload);
      }
      await loadData();
      setShowVariantModal(false);
      setEditingItem(null);
      setVariantForm({
        category_id: null, product_id: null, name: '', price: '', description: '',
        min_quantity: '', max_quantity: '', delivery_time_days: '', time: '',
        smm_service_id: '', smmkings_id: '', api_endpoint: '',
        requires_comments: false, requires_custom_fields: false, custom_fields_config: {},
        drip_feed: false, runs: '', interval: '', drip_quantity: '', is_active: true
      });
    } catch (error) {
      alert('세부서비스 저장 실패');
    }
  };

  const handleDeleteVariant = async (id) => {
    if (!window.confirm('정말 삭제하시겠습니까?')) return;
    try {
      await api.delete(`/admin/product-variants/${id}`);
      await loadData();
    } catch (error) {
      alert('세부서비스 삭제 실패');
    }
  };

  // Package handlers
  const openPackageModal = (pkg = null) => {
    if (pkg) {
      setEditingItem(pkg);
      const meta = pkg.meta_json || {};
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
      });
    } else {
      setEditingItem(null);
      setPackageForm({
        category_id: null, name: '', description: '', price: '',
        min_quantity: '', max_quantity: '', time: '', smmkings_id: '',
        drip_feed: false, runs: '', interval: '', drip_quantity: '', items: []
      });
    }
    setVariantSearchTerms({});
    setShowPackageModal(true);
  };

  const handleSavePackage = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        category_id: packageForm.category_id,
        name: packageForm.name,
        description: packageForm.description,
        items: packageForm.items,
        meta_json: {
          price: parseFloat(packageForm.price) || 0,
          min: parseInt(packageForm.min_quantity) || null,
          max: parseInt(packageForm.max_quantity) || null,
          min_quantity: parseInt(packageForm.min_quantity) || null,
          max_quantity: parseInt(packageForm.max_quantity) || null,
          time: packageForm.time || null,
          smmkings_id: packageForm.smmkings_id || null,
          id: packageForm.smmkings_id || null,
          drip_feed: packageForm.drip_feed,
          runs: packageForm.drip_feed ? parseInt(packageForm.runs) || null : null,
          interval: packageForm.drip_feed ? parseInt(packageForm.interval) || null : null,
          drip_quantity: packageForm.drip_feed ? parseInt(packageForm.drip_quantity) || null : null
        }
      };

      if (editingItem) {
        await api.put(`/admin/packages/${editingItem.package_id}`, payload);
      } else {
        await api.post('/admin/packages', payload);
      }
      await loadData();
      setShowPackageModal(false);
      setEditingItem(null);
      setPackageForm({
        category_id: null, name: '', description: '', price: '',
        min_quantity: '', max_quantity: '', time: '', smmkings_id: '',
        drip_feed: false, runs: '', interval: '', drip_quantity: '', items: []
      });
      setVariantSearchTerms({});
    } catch (error) {
      alert('패키지 저장 실패');
    }
  };

  const handleDeletePackage = async (id) => {
    if (!window.confirm('정말 삭제하시겠습니까?')) return;
    try {
      await api.delete(`/admin/packages/${id}`);
      await loadData();
    } catch (error) {
      alert('패키지 삭제 실패');
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
