import React from 'react';
import { Input } from '@/components/ui/input';

function VariantSearchDropdown({ 
  variants, 
  products, 
  categories, 
  selectedVariantId, 
  searchTerm, 
  onSearchChange, 
  onSelect 
}) {
  const filtered = variants
    .filter(v => v.is_active)
    .filter(v => {
      if (!searchTerm) return true;
      const product = products.find(p => p.product_id === v.product_id);
      return (
        v.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        product?.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        v.price?.toString().includes(searchTerm)
      );
    });

  const selectedVariant = variants.find(v => v.variant_id === selectedVariantId);
  const selectedProduct = selectedVariant ? products.find(p => p.product_id === selectedVariant.product_id) : null;

  return (
    <div className="space-y-2">
      <label className="text-xs font-medium">세부서비스 *</label>
      
      <div className="relative">
        <Input
          type="text"
          placeholder="세부서비스 검색..."
          value={searchTerm}
          onChange={(e) => onSearchChange(e.target.value)}
          className="text-sm pr-8"
        />
        {searchTerm && (
          <button
            type="button"
            onClick={() => onSearchChange('')}
            className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 text-xs"
          >
            ✕
          </button>
        )}
      </div>

      {selectedVariantId && (
        <div className="p-2 bg-blue-50 border border-blue-200 rounded text-xs">
          <span className="font-medium">선택됨:</span>{' '}
          {selectedVariant ? `${selectedVariant.name} ${selectedProduct ? `(${selectedProduct.name})` : ''}` : '없음'}
        </div>
      )}

      {(searchTerm || !selectedVariantId) && (
        <div className="max-h-48 overflow-y-auto border rounded bg-white">
          {filtered.length === 0 ? (
            <div className="p-3 text-center text-gray-500 text-xs">
              {searchTerm ? '검색 결과가 없습니다' : '사용 가능한 세부서비스가 없습니다'}
            </div>
          ) : (
            filtered.map(variant => {
              const product = products.find(p => p.product_id === variant.product_id);
              const category = product ? categories.find(c => c.category_id === product.category_id) : null;
              return (
                <button
                  key={variant.variant_id}
                  type="button"
                  onClick={() => {
                    onSelect(variant.variant_id);
                    onSearchChange('');
                  }}
                  className={`w-full text-left px-3 py-2 hover:bg-blue-50 border-b last:border-b-0 text-xs ${
                    selectedVariantId === variant.variant_id ? 'bg-blue-100' : ''
                  }`}
                >
                  <div className="font-medium">{variant.name}</div>
                  <div className="text-gray-500">
                    {category?.name} &gt; {product?.name} · ₩{variant.price?.toLocaleString()}
                  </div>
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

export default VariantSearchDropdown;

