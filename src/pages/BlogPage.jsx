import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Search, Tag, Calendar, Eye, ArrowRight } from 'lucide-react';
import './BlogPage.css';

const BlogPage = () => {
  const [posts, setPosts] = useState([]);
  const [tags, setTags] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTag, setSelectedTag] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 10,
    total: 0,
    pages: 0
  });

  // 블로그 글 목록 조회
  const fetchPosts = async (page = 1, search = '', tag = '', category = '') => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        page: page.toString(),
        limit: pagination.limit.toString()
      });
      
      if (search) params.append('search', search);
      if (tag) params.append('tag', tag);
      if (category) params.append('category', category);

      const response = await fetch(`/api/blog/posts?${params}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();

      if (data.success) {
        setPosts(data.posts || []);
        setPagination(data.pagination || { page: 1, limit: 10, total: 0, pages: 0 });
      } else {
        console.error('블로그 글 조회 실패:', data.message);
        setPosts([]);
        setPagination({ page: 1, limit: 10, total: 0, pages: 0 });
      }
    } catch (error) {
      console.error('블로그 글 조회 오류:', error);
      setPosts([]);
      setPagination({ page: 1, limit: 10, total: 0, pages: 0 });
    } finally {
      setLoading(false);
    }
  };

  // 태그 목록 조회
  const fetchTags = async () => {
    try {
      const response = await fetch('/api/blog/tags');
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();

      if (data.success) {
        setTags(data.tags || []);
      } else {
        console.error('태그 조회 실패:', data.message);
        setTags([]);
      }
    } catch (error) {
      console.error('태그 조회 오류:', error);
      setTags([]);
    }
  };

  // 카테고리 목록 조회
  const fetchCategories = async () => {
    try {
      const response = await fetch('/api/blog/categories');
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();

      if (data.success) {
        setCategories(data.categories || []);
      } else {
        console.error('카테고리 조회 실패:', data.message);
        setCategories([]);
      }
    } catch (error) {
      console.error('카테고리 조회 오류:', error);
      setCategories([]);
    }
  };

  useEffect(() => {
    fetchPosts();
    fetchTags();
    fetchCategories();
  }, []);

  // 검색 처리
  const handleSearch = (e) => {
    e.preventDefault();
    fetchPosts(1, searchTerm, selectedTag, selectedCategory);
  };

  // 태그 필터 처리
  const handleTagFilter = (tag) => {
    setSelectedTag(tag === selectedTag ? '' : tag);
    fetchPosts(1, searchTerm, tag === selectedTag ? '' : tag, selectedCategory);
  };

  // 카테고리 필터 처리
  const handleCategoryFilter = (category) => {
    setSelectedCategory(category === selectedCategory ? '' : category);
    fetchPosts(1, searchTerm, selectedTag, category === selectedCategory ? '' : category);
  };

  // 페이지네이션 처리
  const handlePageChange = (newPage) => {
    fetchPosts(newPage, searchTerm, selectedTag, selectedCategory);
  };

  // 날짜 포맷팅
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  return (
    <div className="blog-page">
      <div className="blog-container">
        {/* 헤더 */}
        <div className="blog-header">
          <h1>소셜리티 블로그</h1>
          <p>SNS 마케팅의 모든 것을 알려드립니다. 인스타그램, 유튜브, 페이스북 등 다양한 플랫폼의 최신 트렌드와 마케팅 노하우를 만나보세요.</p>
        </div>

        {/* 검색 */}
        <div className="search-section">
          <div className="search-container">
            <input
              type="text"
              placeholder="블로그 글 검색..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
            <button onClick={handleSearch} className="search-button">
              검색
            </button>
          </div>
        </div>

        {/* 카테고리 필터 */}
        <div className="category-nav">
          <button
            className={`category-btn ${selectedCategory === '' ? 'active' : ''}`}
            onClick={() => handleCategoryFilter('')}
          >
            전체보기
          </button>
          <button
            className={`category-btn ${selectedCategory === '인스타그램' ? 'active' : ''}`}
            onClick={() => handleCategoryFilter('인스타그램')}
          >
            인스타그램
          </button>
          <button
            className={`category-btn ${selectedCategory === '소셜리티' ? 'active' : ''}`}
            onClick={() => handleCategoryFilter('소셜리티')}
          >
            소셜리티
          </button>
          <button
            className={`category-btn ${selectedCategory === '네이버' ? 'active' : ''}`}
            onClick={() => handleCategoryFilter('네이버')}
          >
            네이버
          </button>
          <button
            className={`category-btn ${selectedCategory === '유튜브' ? 'active' : ''}`}
            onClick={() => handleCategoryFilter('유튜브')}
          >
            유튜브
          </button>
          <button
            className={`category-btn ${selectedCategory === '틱톡' ? 'active' : ''}`}
            onClick={() => handleCategoryFilter('틱톡')}
          >
            틱톡
          </button>
          <button
            className={`category-btn ${selectedCategory === '업데이트' ? 'active' : ''}`}
            onClick={() => handleCategoryFilter('업데이트')}
          >
            업데이트
          </button>
        </div>

        {/* 블로그 글 목록 */}
        <div className="blog-content">
          {loading ? (
            <div className="loading">
              <div className="loading-spinner"></div>
              <p>블로그 글을 불러오는 중...</p>
            </div>
          ) : posts.length === 0 ? (
            <div className="no-posts">
              <p>아직 작성된 블로그 글이 없습니다.</p>
            </div>
          ) : (
            <div className="posts-list">
              {posts.map((post) => (
                <article key={post.id} className="post-item">
                  <div className="post-thumbnail">
                    {post.thumbnail_url ? (
                      <img src={post.thumbnail_url} alt={post.title} />
                    ) : (
                      <div className="thumbnail-placeholder">
                        <div className="placeholder-content">
                          <span className="placeholder-text">{post.title}</span>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <div className="post-content">
                    <h2 className="post-title">
                      <Link to={`/blog/${post.id}`}>{post.title}</Link>
                    </h2>
                    
                    {post.excerpt && (
                      <div className="post-excerpt">
                        <p>{post.excerpt}</p>
                      </div>
                    )}
                    
                    <div className="post-meta">
                      <span className="post-category">{post.category}</span>
                      <span className="post-date">{formatDate(post.created_at)}</span>
                      <span className="post-views">{post.view_count} 조회</span>
                    </div>
                    
                    <Link to={`/blog/${post.id}`} className="read-more">
                      자세히 보기
                    </Link>
                  </div>
                </article>
              ))}
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
      </div>
    </div>
  );
};

export default BlogPage;
