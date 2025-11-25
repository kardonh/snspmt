import React, { useState } from 'react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { LayoutDashboard, Users, ShoppingCart, Wallet, UserPlus, FileText, Package, MessageSquare, Ticket } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import AdminDashboard from '@/components/admin/AdminDashboard';
import AdminUsers from '@/components/admin/AdminUsers';
import AdminOrders from '@/components/admin/AdminOrders';
import AdminPoints from '@/components/admin/AdminPoints';
import AdminReferrals from '@/components/admin/AdminReferrals';
import AdminBlog from '@/components/admin/AdminBlog';
import AdminServices from '@/components/admin/AdminServices';
import AdminPopup from '@/components/admin/AdminPopup';
import AdminCoupons from '@/components/admin/AdminCoupons';
import './AdminPage.css';

const menuItems = [
  { icon: LayoutDashboard, label: '대시보드', key: 'dashboard' },
  { icon: Users, label: '사용자 관리', key: 'users' },
  { icon: ShoppingCart, label: '주문 관리', key: 'orders' },
  { icon: Wallet, label: '포인트 구매 신청', key: 'points' },
  { icon: UserPlus, label: '추천인 관리', key: 'referrals' },
  { icon: FileText, label: '블로그 관리', key: 'blog' },
  { icon: Package, label: '서비스 관리', key: 'services' },
  { icon: MessageSquare, label: '팝업 관리', key: 'popup' },
  { icon: Ticket, label: '쿠폰 관리', key: 'coupons' },
];

function AdminPage() {
  const { user } = useAuth();
  const [activeMenu, setActiveMenu] = useState(() => {
    return localStorage.getItem('adminActiveTab') || 'dashboard';
  });

  const handleMenuChange = (key) => {
    setActiveMenu(key);
    localStorage.setItem('adminActiveTab', key);
  };

  const renderContent = () => {
    switch (activeMenu) {
      case 'dashboard': return <AdminDashboard />;
      case 'users': return <AdminUsers />;
      case 'orders': return <AdminOrders />;
      case 'points': return <AdminPoints />;
      case 'referrals': return <AdminReferrals />;
      case 'blog': return <AdminBlog />;
      case 'services': return <AdminServices />;
      case 'popup': return <AdminPopup />;
      case 'coupons': return <AdminCoupons />;
      case 'schedules': return <AdminSchedules />;
      default: return <AdminDashboard />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Left: Logo & Title */}
            <div className="flex items-center gap-4">
              <div>
                <h1 className="text-xl font-bold text-gray-900">Sociality Admin</h1>
                <p className="text-sm text-gray-500">관리자 페이지</p>
              </div>
            </div>

            {/* Right: Actions & User */}
            <div className="flex items-center gap-3">
              {/* <Button variant="ghost" size="icon" className="relative">
                <Bell className="h-5 w-5" />
                <Badge className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs">3</Badge>
              </Button>
              <Button variant="ghost" size="icon">
                <Settings className="h-5 w-5" />
              </Button> */}
              <div className="h-8 w-px bg-gray-200" />
              <div className="flex items-center gap-3">
                <Avatar>
                  <AvatarFallback className="bg-blue-500 text-white">
                    {user?.username?.substring(0, 2).toUpperCase() || 'AD'}
                  </AvatarFallback>
                </Avatar>
                <div className="hidden md:block">
                  <p className="text-sm font-medium">{user?.username || 'Admin'}</p>
                  <p className="text-xs text-gray-500">관리자</p>
                </div>
              </div>
              {/* <Button variant="ghost" size="icon" onClick={logout}>
                <LogOut className="h-5 w-5" />
              </Button> */}
            </div>
          </div>
        </div>

        {/* Navigation Bar */}
        <nav className="px-6 border-t border-gray-100">
          <div className="flex gap-1 overflow-x-auto">
            {menuItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.key}
                  onClick={() => handleMenuChange(item.key)}
                  className={`flex items-center gap-2 px-4 py-3 whitespace-nowrap text-sm font-medium transition-colors border-b-2 ${
                    activeMenu === item.key 
                      ? 'border-blue-500 text-blue-600' 
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </button>
              );
            })}
          </div>
        </nav>
      </header>

      {/* Main Content */}
      <main className="p-6">
        {renderContent()}
      </main>
    </div>
  );
}

export default AdminPage;