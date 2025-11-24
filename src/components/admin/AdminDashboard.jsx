import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Users, ShoppingCart, Activity, TrendingUp, Wallet, Download } from 'lucide-react';
import api from '@/services/api';

export default function AdminDashboard() {
  const [data, setData] = useState({
    totalUsers: 0, totalOrders: 0, totalRevenue: 0,
    pendingPurchases: 0, todayOrders: 0, todayRevenue: 0, monthlyRevenue: 0
  });

  const loadStats = async () => {
    try {
      const { data: result } = await api.get('/admin/stats');
      setData({
        totalUsers: result.total_users || 0,
        totalOrders: result.total_orders || 0,
        totalRevenue: result.total_revenue || 0,
        pendingPurchases: result.pending_purchases || 0,
        todayOrders: result.today_orders || 0,
        todayRevenue: result.today_revenue || 0,
        monthlyRevenue: result.monthly_sales || 0
      });
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  useEffect(() => { loadStats(); }, []);

  const stats = [
    { icon: Users, label: '총 사용자', value: data.totalUsers, color: 'bg-blue-500' },
    { icon: ShoppingCart, label: '총 주문', value: data.totalOrders, color: 'bg-green-500' },
    { icon: Activity, label: '대기 중인 구매', value: data.pendingPurchases, color: 'bg-yellow-500' },
    { icon: TrendingUp, label: '오늘 주문', value: data.todayOrders, color: 'bg-purple-500' },
    { icon: Wallet, label: '오늘 매출', value: `₩${data.todayRevenue.toLocaleString()}`, color: 'bg-pink-500' },
    { icon: TrendingUp, label: '월 매출', value: `₩${data.monthlyRevenue.toLocaleString()}`, color: 'bg-indigo-500' }
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {stats.map((stat, i) => (
          <div key={i} className="bg-white rounded-lg shadow p-6 flex items-center gap-4">
            <div className={`${stat.color} text-white p-3 rounded-lg`}>
              <stat.icon className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm text-gray-600">{stat.label}</p>
              <p className="text-2xl font-bold">{stat.value}</p>
            </div>
          </div>
        ))}
      </div>
      
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">데이터 내보내기</h3>
        <div className="flex gap-3">
          {['사용자', '주문', '구매신청'].map(type => (
            <Button key={type} variant="outline">
              <Download className="h-4 w-4 mr-2" />
              {type} 내보내기
            </Button>
          ))}
        </div>
      </div>
    </div>
  );
}

