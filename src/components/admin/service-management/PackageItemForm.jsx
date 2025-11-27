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
    <div className="border p-4 rounded-md relative bg-gray-50">
      <div className="flex justify-between items-center mb-3">
        <h4 className="font-semibold">단계 {item.step || index + 1}</h4>
        <Button
          type="button"
          variant="destructive"
          size="sm"
          onClick={onRemove}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
      
      <div className="space-y-3">
        <div>
          <label className="text-sm font-medium">세부서비스 *</label>
          <VariantSearchDropdown
            variants={variants}
            products={products}
            categories={categories}
            selectedVariantId={item.variant_id}
            searchTerm={searchTerm}
            onSearchChange={onSearchChange}
            onSelect={(variantId) => onUpdate('variant_id', variantId)}
          />
        </div>

        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="text-xs font-medium">수량</label>
            <Input
              type="number"
              value={item.quantity || ''}
              onChange={(e) => onUpdate('quantity', e.target.value ? parseInt(e.target.value) : null)}
              className="mt-1 text-sm"
              placeholder="0"
            />
          </div>
          
          <div>
            <label className="text-xs font-medium">간격 값</label>
            <Input
              type="number"
              value={item.term_value || ''}
              onChange={(e) => onUpdate('term_value', e.target.value ? parseInt(e.target.value) : null)}
              className="mt-1 text-sm"
              placeholder="0"
            />
          </div>
          
          <div>
            <label className="text-xs font-medium">간격 단위</label>
            <select
              value={item.term_unit || 'day'}
              onChange={(e) => onUpdate('term_unit', e.target.value)}
              className="w-full mt-1 px-2 py-1.5 text-sm border rounded"
            >
              <option value="minute">분</option>
              <option value="hour">시</option>
              <option value="day">일</option>
              <option value="week">주</option>
              <option value="month">월</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="text-xs font-medium">반복 횟수</label>
            <Input
              type="number"
              value={item.repeat_count || ''}
              onChange={(e) => onUpdate('repeat_count', e.target.value ? parseInt(e.target.value) : null)}
              className="mt-1 text-sm"
              placeholder="0"
            />
          </div>
          
          <div>
            <label className="text-xs font-medium">반복 간격 값</label>
            <Input
              type="number"
              value={item.repeat_term_value || ''}
              onChange={(e) => onUpdate('repeat_term_value', e.target.value ? parseInt(e.target.value) : null)}
              className="mt-1 text-sm"
              placeholder="0"
            />
          </div>
          
          <div>
            <label className="text-xs font-medium">반복 간격 단위</label>
            <select
              value={item.repeat_term_unit || 'day'}
              onChange={(e) => onUpdate('repeat_term_unit', e.target.value)}
              className="w-full mt-1 px-2 py-1.5 text-sm border rounded"
            >
              <option value="minute">분</option>
              <option value="hour">시</option>
              <option value="day">일</option>
              <option value="week">주</option>
              <option value="month">월</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PackageItemForm;

