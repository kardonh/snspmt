import React from 'react';
import { ChevronRight, ChevronDown, Edit, Trash2, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

function ServiceTreeView({
  categories,
  products,
  variants,
  expandedCategories,
  expandedProducts,
  onToggleCategory,
  onToggleProduct,
  onEditCategory,
  onEditProduct,
  onEditVariant,
  onDeleteCategory,
  onDeleteProduct,
  onDeleteVariant,
  onAddProduct,
  onAddVariant,
  searchTerm = '',
  filteredVariants = null
}) {
  const highlightText = (text, search) => {
    if (!search) return text;
    const parts = text.split(new RegExp(`(${search})`, 'gi'));
    return parts.map((part, i) => 
      part.toLowerCase() === search.toLowerCase() 
        ? <mark key={i} className="bg-yellow-200">{part}</mark> 
        : part
    );
  };

  const isVariantFiltered = (variant) => {
    return filteredVariants ? filteredVariants.some(v => v.variant_id === variant.variant_id) : false;
  };

  return (
    <div className="space-y-2">
      {categories.map(category => {
        const categoryProducts = products.filter(p => p.category_id === category.category_id);
        const isExpanded = expandedCategories.includes(category.category_id);

        return (
          <div key={category.category_id} className="border rounded-lg p-3 bg-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 flex-1">
                <button onClick={() => onToggleCategory(category.category_id)} className="p-1 hover:bg-gray-100 rounded">
                  {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                </button>
                <span className="font-semibold">{category.name}</span>
                <Badge variant={category.is_active ? "default" : "secondary"}>
                  {category.is_active ? '활성' : '비활성'}
                </Badge>
              </div>
              <div className="flex gap-1">
                <Button variant="ghost" size="sm" onClick={() => onAddProduct(category)}>
                  <Plus className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm" onClick={() => onEditCategory(category)}>
                  <Edit className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm" onClick={() => onDeleteCategory(category.category_id)}>
                  <Trash2 className="h-4 w-4 text-red-500" />
                </Button>
              </div>
            </div>

            {isExpanded && (
              <div className="ml-6 mt-2 space-y-2">
                {categoryProducts.map(product => {
                  const productVariants = variants.filter(v => v.product_id === product.product_id);
                  const isProductExpanded = expandedProducts.includes(product.product_id);

                  return (
                    <div key={product.product_id} className="border-l-2 border-gray-200 pl-3">
                      <div className="flex items-center justify-between py-1">
                        <div className="flex items-center gap-2 flex-1">
                          <button onClick={() => onToggleProduct(product.product_id)} className="p-1 hover:bg-gray-100 rounded">
                            {isProductExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                          </button>
                          <span className="font-medium text-sm">{product.name}</span>
                          {product.is_domestic == true && <Badge className="bg-purple-500 text-xs">국내</Badge>}
                          {
                          product.is_domestic == false && <Badge className="bg-red-500 text-xs">해외</Badge>
                          }
                          {product.is_auto && <Badge className="bg-green-500 text-xs">자동</Badge>}
                          {product.auto_tag && <Badge className="bg-blue-500 text-xs">자동태그</Badge>}
                        </div>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm" onClick={() => onAddVariant(product)}>
                            <Plus className="h-3 w-3" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => onEditProduct(product)}>
                            <Edit className="h-3 w-3" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => onDeleteProduct(product.product_id)}>
                            <Trash2 className="h-3 w-3 text-red-500" />
                          </Button>
                        </div>
                      </div>

                      {isProductExpanded && (
                        <div className="ml-4 mt-1 space-y-1">
                          {productVariants.map(variant => {
                            const isHighlighted = isVariantFiltered(variant);
                            return (
                              <div 
                                key={variant.variant_id} 
                                className={`flex items-center justify-between p-2 rounded text-sm ${
                                  isHighlighted ? 'bg-yellow-50 border border-yellow-300' : 'hover:bg-gray-50'
                                }`}
                              >
                                <div className="flex-1">
                                  <span className={isHighlighted ? 'font-semibold' : ''}>
                                    {highlightText(variant.name || '', searchTerm)}
                                  </span>
                                  <span className="text-gray-500 text-xs ml-2">
                                    ₩{highlightText((variant.price || 0).toLocaleString(), searchTerm)}
                                  </span>
                                  {variant.description && (
                                    <p className="text-xs text-gray-400 mt-1">
                                      {highlightText(variant.description, searchTerm)}
                                    </p>
                                  )}
                                </div>
                                <div className="flex gap-1 items-center">
                                  <Badge variant={variant.is_active ? "default" : "secondary"} className="text-xs">
                                    {variant.is_active ? '활성' : '비활성'}
                                  </Badge>
                                  <Button variant="ghost" size="sm" onClick={() => onEditVariant(variant)}>
                                    <Edit className="h-3 w-3" />
                                  </Button>
                                  <Button variant="ghost" size="sm" onClick={() => onDeleteVariant(variant.variant_id)}>
                                    <Trash2 className="h-3 w-3 text-red-500" />
                                  </Button>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default ServiceTreeView;

