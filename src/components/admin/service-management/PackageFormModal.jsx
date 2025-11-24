import React from 'react';
import { Plus } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import PackageItemForm from './PackageItemForm';

function PackageFormModal({ 
  open, 
  onOpenChange, 
  packageForm, 
  onFormChange, 
  categories, 
  variants, 
  products, 
  variantSearchTerms, 
  onSearchTermChange, 
  onSubmit, 
  editingItem 
}) {
  const addItem = () => {
    onFormChange({
      ...packageForm,
      items: [...packageForm.items, { variant_id: null, quantity: 0, term: 0, repeat: 0 }]
    });
  };

  const removeItem = (index) => {
    onFormChange({
      ...packageForm,
      items: packageForm.items.filter((_, i) => i !== index)
    });
  };

  const updateItem = (index, field, value) => {
    const updated = [...packageForm.items];
    updated[index] = { ...updated[index], [field]: value };
    onFormChange({ ...packageForm, items: updated });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[800px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{editingItem ? '패키지 수정' : '새 패키지 추가'}</DialogTitle>
        </DialogHeader>

        <form onSubmit={onSubmit} className="grid gap-4 py-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium">카테고리 *</label>
              <select
                value={packageForm.category_id || ''}
                onChange={(e) => onFormChange({ ...packageForm, category_id: parseInt(e.target.value) })}
                required
                className="w-full mt-1 px-3 py-2 border rounded"
              >
                <option value="">선택하세요</option>
                {categories.map(cat => (
                  <option key={cat.category_id} value={cat.category_id}>{cat.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-sm font-medium">이름 *</label>
              <Input
                value={packageForm.name}
                onChange={(e) => onFormChange({ ...packageForm, name: e.target.value })}
                required
              />
            </div>
          </div>

          <div>
            <label className="text-sm font-medium">설명</label>
            <Textarea
              value={packageForm.description}
              onChange={(e) => onFormChange({ ...packageForm, description: e.target.value })}
              rows={2}
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-sm font-medium">가격 *</label>
              <Input
                type="number"
                value={packageForm.price}
                onChange={(e) => onFormChange({ ...packageForm, price: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="text-sm font-medium">최소 수량</label>
              <Input
                type="number"
                value={packageForm.min_quantity}
                onChange={(e) => onFormChange({ ...packageForm, min_quantity: e.target.value })}
              />
            </div>
            <div>
              <label className="text-sm font-medium">최대 수량</label>
              <Input
                type="number"
                value={packageForm.max_quantity}
                onChange={(e) => onFormChange({ ...packageForm, max_quantity: e.target.value })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium">시간 (시작-끝)</label>
              <Input
                value={packageForm.time}
                onChange={(e) => onFormChange({ ...packageForm, time: e.target.value })}
                placeholder="0-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">SMM Kings ID</label>
              <Input
                value={packageForm.smmkings_id}
                onChange={(e) => onFormChange({ ...packageForm, smmkings_id: e.target.value })}
              />
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="drip_feed"
              checked={packageForm.drip_feed}
              onCheckedChange={(checked) => onFormChange({ ...packageForm, drip_feed: checked })}
            />
            <label htmlFor="drip_feed" className="text-sm font-medium">드립 피드 활성화</label>
          </div>

          {packageForm.drip_feed && (
            <div className="grid grid-cols-3 gap-3 bg-gray-50 p-3 rounded">
              <div>
                <label className="text-xs font-medium">실행 횟수</label>
                <Input
                  type="number"
                  value={packageForm.runs}
                  onChange={(e) => onFormChange({ ...packageForm, runs: e.target.value })}
                  className="text-sm"
                />
              </div>
              <div>
                <label className="text-xs font-medium">간격 (분)</label>
                <Input
                  type="number"
                  value={packageForm.interval}
                  onChange={(e) => onFormChange({ ...packageForm, interval: e.target.value })}
                  className="text-sm"
                />
              </div>
              <div>
                <label className="text-xs font-medium">드립 수량</label>
                <Input
                  type="number"
                  value={packageForm.drip_quantity}
                  onChange={(e) => onFormChange({ ...packageForm, drip_quantity: e.target.value })}
                  className="text-sm"
                />
              </div>
            </div>
          )}

          <h3 className="text-lg font-semibold mt-4">패키지 아이템</h3>
          {packageForm.items.map((item, index) => (
            <PackageItemForm
              key={index}
              item={item}
              index={index}
              variants={variants}
              products={products}
              categories={categories}
              searchTerm={variantSearchTerms[index] || ''}
              onSearchChange={(term) => onSearchTermChange(index, term)}
              onUpdate={(field, value) => updateItem(index, field, value)}
              onRemove={() => removeItem(index)}
            />
          ))}

          <Button type="button" variant="outline" onClick={addItem}>
            <Plus className="h-4 w-4 mr-2" /> 아이템 추가
          </Button>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>취소</Button>
            <Button type="submit">저장</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default PackageFormModal;

