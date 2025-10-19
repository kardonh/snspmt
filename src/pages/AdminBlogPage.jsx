import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Edit, Trash2, Eye, Search, Tag, Calendar } from 'lucide-react';
import './AdminBlogPage.css';

const AdminBlogPage = () => {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingPost, setEditingPost] = useState(null);
  const [uploadingThumbnail, setUploadingThumbnail] = useState(false);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 10,
    total: 0,
    pages: 0
  });

  // 폼 데이터
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    excerpt: '',
    category: '일반',
    thumbnail_url: '',
    tags: [],
    is_published: true
  });

  // 블로그 글 목록 조회 (관리자용 - 모든 글)
  const fetchPosts = async (page = 1, search = '') => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        page: page.toString(),
        limit: pagination.limit.toString(),
        admin: 'true' // 관리자 모드
      });
      
      if (search) params.append('search', search);

      const response = await fetch(`/api/blog/posts?${params}`, {
        headers: {
          'X-Admin-Token': 'admin_sociality_2024' // 관리자 토큰
        }
      });
      const data = await response.json();

      if (data.success) {
        setPosts(data.posts);
        setPagination(data.pagination);
      } else {
        console.error('블로그 글 조회 실패:', data.message);
      }
    } catch (error) {
      console.error('블로그 글 조회 오류:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPosts();
  }, []);

  // 검색 처리
  const handleSearch = (e) => {
    e.preventDefault();
    fetchPosts(1, searchTerm);
  };

  // 페이지네이션 처리
  const handlePageChange = (newPage) => {
    fetchPosts(newPage, searchTerm);
  };

  // 폼 데이터 변경
  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  // 썸네일 이미지 업로드
  const handleThumbnailUpload = async (file) => {
    try {
      setUploadingThumbnail(true);
      
      const formData = new FormData();
      formData.append('image', file);
      
      const response = await fetch('/api/admin/upload-image', {
        method: 'POST',
        headers: {
          'X-Admin-Token': 'admin_sociality_2024'
        },
        body: formData
      });
      
      const data = await response.json();
      
      if (data.success) {
        setFormData(prev => ({
          ...prev,
          thumbnail_url: data.image_url
        }));
        alert('썸네일 이미지가 업로드되었습니다.');
      } else {
        alert(data.message || '이미지 업로드에 실패했습니다.');
      }
    } catch (error) {
      console.error('썸네일 업로드 오류:', error);
      alert('이미지 업로드 중 오류가 발생했습니다.');
    } finally {
      setUploadingThumbnail(false);
    }
  };

  // 태그 입력 처리
  const handleTagsChange = (e) => {
    const tags = e.target.value.split(',').map(tag => tag.trim()).filter(tag => tag);
    setFormData(prev => ({
      ...prev,
      tags
    }));
  };

  // 글 작성
  const handleCreatePost = async (e) => {
    e.preventDefault();
    
    try {
      const response = await fetch('/api/blog/posts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Token': 'admin_sociality_2024' // 관리자 토큰
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (data.success) {
        alert('블로그 글이 작성되었습니다.');
        setShowCreateModal(false);
        setFormData({
          title: '',
          content: '',
          excerpt: '',
          category: '일반',
          thumbnail_url: '',
          tags: [],
          is_published: true
        });
        fetchPosts();
      } else {
        alert(data.message || '블로그 글 작성에 실패했습니다.');
      }
    } catch (error) {
      console.error('블로그 글 작성 오류:', error);
      alert('블로그 글 작성 중 오류가 발생했습니다.');
    }
  };

  // 글 수정
  const handleEditPost = async (e) => {
    e.preventDefault();
    
    try {
      const response = await fetch(`/api/blog/posts/${editingPost.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Token': 'admin_sociality_2024' // 관리자 토큰
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (data.success) {
        alert('블로그 글이 수정되었습니다.');
        setShowEditModal(false);
        setEditingPost(null);
        setFormData({
          title: '',
          content: '',
          excerpt: '',
          category: '일반',
          thumbnail_url: '',
          tags: [],
          is_published: true
        });
        fetchPosts();
      } else {
        alert(data.message || '블로그 글 수정에 실패했습니다.');
      }
    } catch (error) {
      console.error('블로그 글 수정 오류:', error);
      alert('블로그 글 수정 중 오류가 발생했습니다.');
    }
  };

  // 글 삭제
  const handleDeletePost = async (postId) => {
    if (!confirm('정말로 이 블로그 글을 삭제하시겠습니까?')) {
      return;
    }

    try {
      const response = await fetch(`/api/blog/posts/${postId}`, {
        method: 'DELETE',
        headers: {
          'X-Admin-Token': 'admin_sociality_2024' // 관리자 토큰
        }
      });

      const data = await response.json();

      if (data.success) {
        alert('블로그 글이 삭제되었습니다.');
        fetchPosts();
      } else {
        alert(data.message || '블로그 글 삭제에 실패했습니다.');
      }
    } catch (error) {
      console.error('블로그 글 삭제 오류:', error);
      alert('블로그 글 삭제 중 오류가 발생했습니다.');
    }
  };

  // 수정 모달 열기
  const openEditModal = (post) => {
    setEditingPost(post);
    setFormData({
      title: post.title,
      content: post.content,
      excerpt: post.excerpt || '',
      category: post.category || '일반',
      thumbnail_url: post.thumbnail_url || '',
      tags: post.tags || [],
      is_published: post.is_published
    });
    setShowEditModal(true);
  };

  // 날짜 포맷팅
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <div className="admin-blog-page">
      <div className="admin-blog-container">
        {/* 헤더 */}
        <div className="admin-blog-header">
          <h1>블로그 관리</h1>
          <button 
            className="create-button"
            onClick={() => setShowCreateModal(true)}
          >
            <Plus className="button-icon" />
            새 글 작성
          </button>
        </div>

        {/* 검색 */}
        <div className="admin-blog-filters">
          <form onSubmit={handleSearch} className="search-form">
            <div className="search-input-group">
              <Search className="search-icon" />
              <input
                type="text"
                placeholder="블로그 글 검색..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="search-input"
              />
              <button type="submit" className="search-button">
                검색
              </button>
            </div>
          </form>
        </div>

        {/* 블로그 글 목록 */}
        <div className="admin-blog-content">
          {loading ? (
            <div className="loading">
              <div className="loading-spinner"></div>
              <p>블로그 글을 불러오는 중...</p>
            </div>
          ) : posts.length === 0 ? (
            <div className="no-posts">
              <p>작성된 블로그 글이 없습니다.</p>
            </div>
          ) : (
            <div className="posts-table">
              <table>
                <thead>
                  <tr>
                    <th>제목</th>
                    <th>카테고리</th>
                    <th>상태</th>
                    <th>조회수</th>
                    <th>작성일</th>
                    <th>작업</th>
                  </tr>
                </thead>
                <tbody>
                  {posts.map((post) => (
                    <tr key={post.id}>
                      <td className="post-title-cell">
                        <Link to={`/blog/${post.id}`} className="post-title-link">
                          {post.title}
                        </Link>
                        {post.excerpt && (
                          <div className="post-excerpt">{post.excerpt}</div>
                        )}
                      </td>
                      <td>
                        <span className="category-badge">{post.category}</span>
                      </td>
                      <td>
                        <span className={`status-badge ${post.is_published ? 'published' : 'draft'}`}>
                          {post.is_published ? '발행' : '임시저장'}
                        </span>
                      </td>
                      <td>{post.view_count}</td>
                      <td>{formatDate(post.created_at)}</td>
                      <td className="actions">
                        <button
                          className="action-button view"
                          onClick={() => window.open(`/blog/${post.id}`, '_blank')}
                        >
                          <Eye className="action-icon" />
                        </button>
                        <button
                          className="action-button edit"
                          onClick={() => openEditModal(post)}
                        >
                          <Edit className="action-icon" />
                        </button>
                        <button
                          className="action-button delete"
                          onClick={() => handleDeletePost(post.id)}
                        >
                          <Trash2 className="action-icon" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* 페이지네이션 */}
          {pagination.pages > 1 && (
            <div className="pagination">
              <button
                className="pagination-button"
                onClick={() => handlePageChange(pagination.page - 1)}
                disabled={pagination.page === 1}
              >
                이전
              </button>
              
              {Array.from({ length: pagination.pages }, (_, i) => i + 1).map((page) => (
                <button
                  key={page}
                  className={`pagination-button ${pagination.page === page ? 'active' : ''}`}
                  onClick={() => handlePageChange(page)}
                >
                  {page}
                </button>
              ))}
              
              <button
                className="pagination-button"
                onClick={() => handlePageChange(pagination.page + 1)}
                disabled={pagination.page === pagination.pages}
              >
                다음
              </button>
            </div>
          )}
        </div>

        {/* 글 작성 모달 */}
        {showCreateModal && (
          <div className="modal-overlay">
            <div className="modal">
              <div className="modal-header">
                <h2>새 블로그 글 작성</h2>
                <button 
                  className="close-button"
                  onClick={() => setShowCreateModal(false)}
                >
                  ×
                </button>
              </div>
              <form onSubmit={handleCreatePost} className="post-form">
                <div className="form-group">
                  <label htmlFor="title">제목 *</label>
                  <input
                    type="text"
                    id="title"
                    name="title"
                    value={formData.title}
                    onChange={handleInputChange}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="category">카테고리 *</label>
                  <select
                    id="category"
                    name="category"
                    value={formData.category}
                    onChange={handleInputChange}
                    required
                  >
                    <option value="일반">일반</option>
                    <option value="인스타그램">인스타그램</option>
                    <option value="소셜리티">소셜리티</option>
                    <option value="네이버">네이버</option>
                    <option value="유튜브">유튜브</option>
                    <option value="틱톡">틱톡</option>
                    <option value="업데이트">업데이트</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="thumbnail">썸네일 이미지</label>
                  <div className="image-upload-container">
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => {
                        const file = e.target.files[0];
                        if (file) {
                          handleThumbnailUpload(file);
                        }
                      }}
                      className="file-input"
                      id="thumbnail"
                      disabled={uploadingThumbnail}
                    />
                    <label htmlFor="thumbnail" className="file-input-label">
                      {uploadingThumbnail ? '업로드 중...' : '이미지 선택'}
                    </label>
                    {formData.thumbnail_url && (
                      <div className="uploaded-image">
                        <img src={formData.thumbnail_url} alt="썸네일 미리보기" />
                        <button
                          type="button"
                          onClick={() => setFormData(prev => ({ ...prev, thumbnail_url: '' }))}
                          className="remove-image"
                        >
                          ×
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="excerpt">요약</label>
                  <textarea
                    id="excerpt"
                    name="excerpt"
                    value={formData.excerpt}
                    onChange={handleInputChange}
                    rows="3"
                    placeholder="글의 요약을 입력하세요..."
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="content">내용 *</label>
                  <textarea
                    id="content"
                    name="content"
                    value={formData.content}
                    onChange={handleInputChange}
                    rows="10"
                    required
                    placeholder="블로그 글 내용을 입력하세요..."
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="tags">태그</label>
                  <input
                    type="text"
                    id="tags"
                    value={formData.tags.join(', ')}
                    onChange={handleTagsChange}
                    placeholder="태그를 쉼표로 구분하여 입력하세요..."
                  />
                </div>

                <div className="form-group checkbox-group">
                  <label>
                    <input
                      type="checkbox"
                      name="is_published"
                      checked={formData.is_published}
                      onChange={handleInputChange}
                    />
                    즉시 발행
                  </label>
                </div>

                <div className="form-actions">
                  <button type="button" onClick={() => setShowCreateModal(false)}>
                    취소
                  </button>
                  <button type="submit">작성</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* 글 수정 모달 */}
        {showEditModal && (
          <div className="modal-overlay">
            <div className="modal">
              <div className="modal-header">
                <h2>블로그 글 수정</h2>
                <button 
                  className="close-button"
                  onClick={() => setShowEditModal(false)}
                >
                  ×
                </button>
              </div>
              <form onSubmit={handleEditPost} className="post-form">
                <div className="form-group">
                  <label htmlFor="edit-title">제목 *</label>
                  <input
                    type="text"
                    id="edit-title"
                    name="title"
                    value={formData.title}
                    onChange={handleInputChange}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="edit-category">카테고리 *</label>
                  <select
                    id="edit-category"
                    name="category"
                    value={formData.category}
                    onChange={handleInputChange}
                    required
                  >
                    <option value="일반">일반</option>
                    <option value="인스타그램">인스타그램</option>
                    <option value="소셜리티">소셜리티</option>
                    <option value="네이버">네이버</option>
                    <option value="유튜브">유튜브</option>
                    <option value="틱톡">틱톡</option>
                    <option value="업데이트">업데이트</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="edit-thumbnail">썸네일 이미지</label>
                  <div className="image-upload-container">
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => {
                        const file = e.target.files[0];
                        if (file) {
                          handleThumbnailUpload(file);
                        }
                      }}
                      className="file-input"
                      id="edit-thumbnail"
                      disabled={uploadingThumbnail}
                    />
                    <label htmlFor="edit-thumbnail" className="file-input-label">
                      {uploadingThumbnail ? '업로드 중...' : '이미지 선택'}
                    </label>
                    {formData.thumbnail_url && (
                      <div className="uploaded-image">
                        <img src={formData.thumbnail_url} alt="썸네일 미리보기" />
                        <button
                          type="button"
                          onClick={() => setFormData(prev => ({ ...prev, thumbnail_url: '' }))}
                          className="remove-image"
                        >
                          ×
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="edit-excerpt">요약</label>
                  <textarea
                    id="edit-excerpt"
                    name="excerpt"
                    value={formData.excerpt}
                    onChange={handleInputChange}
                    rows="3"
                    placeholder="글의 요약을 입력하세요..."
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="edit-content">내용 *</label>
                  <textarea
                    id="edit-content"
                    name="content"
                    value={formData.content}
                    onChange={handleInputChange}
                    rows="10"
                    required
                    placeholder="블로그 글 내용을 입력하세요..."
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="edit-tags">태그</label>
                  <input
                    type="text"
                    id="edit-tags"
                    value={formData.tags.join(', ')}
                    onChange={handleTagsChange}
                    placeholder="태그를 쉼표로 구분하여 입력하세요..."
                  />
                </div>

                <div className="form-group checkbox-group">
                  <label>
                    <input
                      type="checkbox"
                      name="is_published"
                      checked={formData.is_published}
                      onChange={handleInputChange}
                    />
                    발행 상태
                  </label>
                </div>

                <div className="form-actions">
                  <button type="button" onClick={() => setShowEditModal(false)}>
                    취소
                  </button>
                  <button type="submit">수정</button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminBlogPage;
