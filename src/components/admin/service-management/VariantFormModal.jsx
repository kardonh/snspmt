import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';

function VariantFormModal({ open, onOpenChange, form, onFormChange, products, categories, onSubmit, isEditing }) {
  const getProductsByCategory = () => {
    if (!form.category_id) return [];
    return products.filter(p => p.category_id === parseInt(form.category_id));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEditing ? '세부서비스 수정' : '새 세부서비스 추가'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmit} className="grid gap-4 py-4">
          <div>
            <label className="text-sm font-medium">카테고리 *</label>
            <select
              value={form.category_id || ''}
              onChange={(e) => onFormChange({ ...form, category_id: e.target.value, product_id: null })}
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
            <label className="text-sm font-medium">상품 *</label>
            <select
              value={form.product_id || ''}
              onChange={(e) => onFormChange({ ...form, product_id: parseInt(e.target.value) })}
              required
              disabled={!form.category_id}
              className="w-full mt-1 px-3 py-2 border rounded"
            >
              <option value="">선택하세요</option>
              {getProductsByCategory().map(prod => (
                <option key={prod.product_id} value={prod.product_id}>{prod.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-sm font-medium">세부서비스 이름 *</label>
            <Input
              value={form.name}
              onChange={(e) => onFormChange({ ...form, name: e.target.value })}
              required
              placeholder="예: KR 인스타그램 한국인 ❤️ 파워업 좋아요"
            />
          </div>

          <div>
            <label className="text-sm font-medium">가격 *</label>
            <Input
              type="number"
              value={form.price}
              onChange={(e) => onFormChange({ ...form, price: e.target.value })}
              required
              min="0"
              step="0.01"
              placeholder="예: 20000"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium">최소 수량</label>
              <Input
                type="number"
                value={form.min_quantity}
                onChange={(e) => onFormChange({ ...form, min_quantity: e.target.value })}
                min="0"
                placeholder="예: 30"
              />
            </div>
            <div>
              <label className="text-sm font-medium">최대 수량</label>
              <Input
                type="number"
                value={form.max_quantity}
                onChange={(e) => onFormChange({ ...form, max_quantity: e.target.value })}
                min="0"
                placeholder="예: 2500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium">배송 시간 (일)</label>
              <Input
                type="number"
                value={form.delivery_time_days || ''}
                onChange={(e) => onFormChange({ ...form, delivery_time_days: e.target.value })}
                min="0"
                placeholder="예: 1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">배송 시간 (문자열)</label>
              <Input
                value={form.time}
                onChange={(e) => onFormChange({ ...form, time: e.target.value })}
                placeholder="예: 14시간 54분"
              />
            </div>
          </div>

          <div>
            <label className="text-sm font-medium">상세정보 (Description)</label>
            <Textarea
              value={form.description}
              onChange={(e) => onFormChange({ ...form, description: e.target.value })}
              rows={3}
              placeholder="서비스 상세 설명"
            />
          </div>

          <div>
            <label className="text-sm font-medium">SMM Panel 서비스 ID</label>
            <Input
              type="number"
              value={form.smmkings_id || form.smm_service_id || ''}
              onChange={(e) => onFormChange({ ...form, smmkings_id: e.target.value, smm_service_id: e.target.value })}
              min="0"
              placeholder="예: 122"
            />
          </div>

          <div>
            <label className="text-sm font-medium">API 엔드포인트</label>
            <Input
              value={form.api_endpoint || ''}
              onChange={(e) => onFormChange({ ...form, api_endpoint: e.target.value })}
              placeholder="SMM Panel API 엔드포인트"
            />
            <p className="text-xs text-gray-500 mt-1">
              환경변수 SMMPANEL_API_ENDPOINT에서 자동으로 로드됩니다.
            </p>
          </div>

          {/* 추가 정보 입력 필드 */}
          <div className="border-t pt-4 mt-2">
            <h4 className="font-semibold mb-3 text-sm">추가 정보 입력 필드 설정</h4>
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="requires_comments"
                  checked={form.requires_comments || false}
                  onCheckedChange={(checked) => onFormChange({ ...form, requires_comments: checked })}
                />
                <label htmlFor="requires_comments" className="text-sm">댓글 필드 필요</label>
              </div>
              <p className="text-xs text-gray-500 ml-6">주문 시 댓글을 입력받습니다</p>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="requires_custom_fields"
                  checked={form.requires_custom_fields || false}
                  onCheckedChange={(checked) => onFormChange({ ...form, requires_custom_fields: checked })}
                />
                <label htmlFor="requires_custom_fields" className="text-sm">커스텀 필드 필요</label>
              </div>
              <p className="text-xs text-gray-500 ml-6">주문 시 추가 정보를 입력받습니다</p>

              {form.requires_custom_fields && (
                <div className="ml-6 mt-2">
                  <label className="text-sm font-medium">커스텀 필드 설정 (JSON)</label>
                  <Textarea
                    value={typeof form.custom_fields_config === 'string' 
                      ? form.custom_fields_config 
                      : JSON.stringify(form.custom_fields_config || {}, null, 2)}
                    onChange={(e) => {
                      try {
                        const parsed = JSON.parse(e.target.value);
                        onFormChange({ ...form, custom_fields_config: parsed });
                      } catch {
                        onFormChange({ ...form, custom_fields_config: e.target.value });
                      }
                    }}
                    rows={4}
                    className="font-mono text-xs"
                    placeholder='{"field1": {"label": "필드명", "type": "text", "required": true}, ...}'
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    JSON 형식으로 커스텀 필드를 설정합니다.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Drip-feed 설정 */}
          <div className="border-t pt-4 mt-2">
            <h4 className="font-semibold mb-3 text-sm">Drip-feed 설정</h4>
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="drip_feed"
                  checked={form.drip_feed || false}
                  onCheckedChange={(checked) => onFormChange({ ...form, drip_feed: checked })}
                />
                <label htmlFor="drip_feed" className="text-sm font-medium">Drip-feed 사용</label>
              </div>

              {form.drip_feed && (
                <div className="ml-6 space-y-3 bg-gray-50 p-3 rounded">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-sm font-medium">실행 횟수 (runs)</label>
                      <Input
                        type="number"
                        value={form.runs || ''}
                        onChange={(e) => onFormChange({ ...form, runs: e.target.value })}
                        min="1"
                        placeholder="예: 30"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium">간격 (분)</label>
                      <Input
                        type="number"
                        value={form.interval || ''}
                        onChange={(e) => onFormChange({ ...form, interval: e.target.value })}
                        min="1"
                        placeholder="예: 1440"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium">Drip-feed 수량</label>
                    <Input
                      type="number"
                      value={form.drip_quantity || ''}
                      onChange={(e) => onFormChange({ ...form, drip_quantity: e.target.value })}
                      min="1"
                      placeholder="예: 400"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-2 pt-2">
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

export default VariantFormModal;