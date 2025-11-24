import React from 'react';
import { Edit, Trash2, Package } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

function PackageList({ packages, categories, onEdit, onDelete }) {
  return (
    <div className="space-y-3">
      {packages.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <Package className="h-12 w-12 mx-auto mb-2 text-gray-300" />
          <p>등록된 패키지가 없습니다</p>
        </div>
      ) : (
        packages.map(pkg => {
          const category = categories.find(c => c.category_id === pkg.category_id);
          const meta = pkg.meta_json || {};
          
          return (
            <div key={pkg.package_id} className="border rounded-lg p-4 bg-white hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="font-semibold text-lg">{pkg.name}</h3>
                    {category && (
                      <Badge variant="outline" className="text-xs">
                        {category.name}
                      </Badge>
                    )}
                    {meta.drip_feed && (
                      <Badge className="bg-purple-500 text-xs">드립 피드</Badge>
                    )}
                  </div>
                  
                  {pkg.description && (
                    <p className="text-sm text-gray-600 mb-2">{pkg.description}</p>
                  )}
                  
                  <div className="flex flex-wrap gap-3 text-sm text-gray-700">
                    <span className="font-medium">₩{(meta.price || 0).toLocaleString()}</span>
                    {meta.min_quantity && <span>최소: {meta.min_quantity}</span>}
                    {meta.max_quantity && <span>최대: {meta.max_quantity}</span>}
                    {meta.time && <span>시간: {meta.time}</span>}
                  </div>
                  
                  {pkg.items && pkg.items.length > 0 && (
                    <div className="mt-3 text-xs text-gray-500">
                      <span className="font-medium">아이템: </span>
                      {pkg.items.length}개 단계
                    </div>
                  )}
                </div>
                
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => onEdit(pkg)}>
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => onDelete(pkg.package_id)}>
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                </div>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}

export default PackageList;

