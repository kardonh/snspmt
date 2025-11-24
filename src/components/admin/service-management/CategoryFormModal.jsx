import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';

function CategoryFormModal({ open, onOpenChange, form, onFormChange, onSubmit, isEditing }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEditing ? '카테고리 수정' : '새 카테고리 추가'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmit} className="grid gap-4 py-4">
          <div>
            <label className="text-sm font-medium">이름 *</label>
            <Input
              value={form.name}
              onChange={(e) => onFormChange({ ...form, name: e.target.value })}
              required
              placeholder="예: Instagram"
            />
          </div>
          <div>
            <label className="text-sm font-medium">슬러그</label>
            <Input
              value={form.slug || ''}
              onChange={(e) => onFormChange({ ...form, slug: e.target.value })}
              placeholder="예: instagram (URL용, 소문자/하이픈만)"
            />
          </div>
          <div>
            <label className="text-sm font-medium">이미지 URL</label>
            <Input
              value={form.image_url || ''}
              onChange={(e) => onFormChange({ ...form, image_url: e.target.value })}
              placeholder="https://example.com/image.png"
            />
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="is_active"
              checked={form.is_active}
              onCheckedChange={(checked) => onFormChange({ ...form, is_active: checked })}
            />
            <label htmlFor="is_active" className="text-sm font-medium">활성화</label>
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

export default CategoryFormModal;

