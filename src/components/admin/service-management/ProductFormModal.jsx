import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';

function ProductFormModal({ open, onOpenChange, form, onFormChange, categories, onSubmit, isEditing }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEditing ? '상품 수정' : '새 상품 추가'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmit} className="grid gap-4 py-4">
          <div>
            <label className="text-sm font-medium">카테고리 *</label>
            <select
              value={form.category_id || ''}
              onChange={(e) => onFormChange({ ...form, category_id: parseInt(e.target.value) })}
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
            <label className="text-sm font-medium">상품 이름 *</label>
            <Input
              value={form.name}
              onChange={(e) => onFormChange({ ...form, name: e.target.value })}
              required
              placeholder="예: 좋아요"
            />
          </div>

          <div>
            <label className="text-sm font-medium">설명</label>
            <Textarea
              value={form.description || ''}
              onChange={(e) => onFormChange({ ...form, description: e.target.value })}
              rows={3}
              placeholder="상품에 대한 설명을 입력하세요"
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="is_domestic"
                checked={form.is_domestic}
                onCheckedChange={(checked) => onFormChange({ ...form, is_domestic: checked })}
              />
              <label htmlFor="is_domestic" className="text-sm font-medium">국내 서비스</label>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="is_auto"
                checked={form.is_auto}
                onCheckedChange={(checked) => onFormChange({ ...form, is_auto: checked })}
              />
              <label htmlFor="is_auto" className="text-sm font-medium">자동상품</label>
              {form.is_auto && <Badge className="bg-green-500">자동</Badge>}
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="auto_tag"
                checked={form.auto_tag}
                onCheckedChange={(checked) => onFormChange({ ...form, auto_tag: checked })}
              />
              <label htmlFor="auto_tag" className="text-sm font-medium">자동 태그</label>
              {form.auto_tag && <Badge className="bg-blue-500">자동 태그</Badge>}
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>취소</Button>
            <Button type="submit">저장</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default ProductFormModal;

