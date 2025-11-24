import React from 'react';
import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import VariantSearchDropdown from './VariantSearchDropdown';

function PackageItemForm({ 
  item, 
  index, 
  variants, 
  products, 
  categories, 
  searchTerm, 
  onSearchChange, 
  onUpdate, 
  onRemove 
}) {
  return (
    <div className="border p-3 rounded-md relative">
      <h4 className="font-medium mb-2">단계 {index + 1}</h4>
      
      <div className="space-y-3">
        <VariantSearchDropdown
          variants={variants}
          products={products}
          categories={categories}
          selectedVariantId={item.variant_id}
          searchTerm={searchTerm}
          onSearchChange={onSearchChange}
          onSelect={(variantId) => onUpdate('variant_id', variantId)}
        />

        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="text-xs font-medium">수량 *</label>
            <Input
              type="number"
              value={item.quantity || ''}
              onChange={(e) => onUpdate('quantity', parseInt(e.target.value) || 0)}
              required
              className="mt-1 text-sm"
            />
          </div>
          
          <div>
            <label className="text-xs font-medium">기간 (일)</label>
            <Input
              type="number"
              value={item.term || ''}
              onChange={(e) => onUpdate('term', parseInt(e.target.value) || 0)}
              className="mt-1 text-sm"
            />
          </div>
          
          <div>
            <label className="text-xs font-medium">반복 횟수</label>
            <Input
              type="number"
              value={item.repeat || ''}
              onChange={(e) => onUpdate('repeat', parseInt(e.target.value) || 0)}
              className="mt-1 text-sm"
            />
          </div>
        </div>
      </div>

      <Button
        type="button"
        variant="destructive"
        size="sm"
        onClick={onRemove}
        className="absolute top-2 right-2"
      >
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  );
}

export default PackageItemForm;

