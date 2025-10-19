import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Calendar, Eye, Tag, Share2 } from 'lucide-react';
import './BlogDetailPage.css';

const BlogDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchPost();
  }, [id]);

  const fetchPost = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await fetch(`/api/blog/posts/${id}`);
      const data = await response.json();

      if (data.success) {
        setPost(data.post);
      } else {
        setError(data.message || '블로그 글을 찾을 수 없습니다.');
      }
    } catch (error) {
      console.error('블로그 글 조회 오류:', error);
      setError('블로그 글을 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: post.title,
          text: post.excerpt,
          url: window.location.href
        });
      } catch (error) {
        console.log('공유 취소됨');
      }
    } else {
      // 클립보드에 URL 복사
      try {
        await navigator.clipboard.writeText(window.location.href);
        alert('링크가 클립보드에 복사되었습니다.');
      } catch (error) {
        console.error('클립보드 복사 실패:', error);
      }
    }
  };

  if (loading) {
    return (
      <div className="blog-detail-page">
        <div className="blog-detail-container">
          <div className="loading">
            <div className="loading-spinner"></div>
            <p>블로그 글을 불러오는 중...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="blog-detail-page">
        <div className="blog-detail-container">
          <div className="error">
            <h2>오류가 발생했습니다</h2>
            <p>{error}</p>
            <button onClick={() => navigate('/blog')} className="back-button">
              <ArrowLeft className="back-icon" />
              블로그 목록으로 돌아가기
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!post) {
    return (
      <div className="blog-detail-page">
        <div className="blog-detail-container">
          <div className="not-found">
            <h2>블로그 글을 찾을 수 없습니다</h2>
            <p>요청하신 블로그 글이 존재하지 않거나 삭제되었습니다.</p>
            <button onClick={() => navigate('/blog')} className="back-button">
              <ArrowLeft className="back-icon" />
              블로그 목록으로 돌아가기
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="blog-detail-page">
      <div className="blog-detail-container">
        {/* 뒤로가기 버튼 */}
        <div className="back-navigation">
          <button onClick={() => navigate('/blog')} className="back-button">
            <ArrowLeft className="back-icon" />
            블로그 목록
          </button>
        </div>

        {/* 블로그 글 헤더 */}
        <header className="post-header">
          <h1 className="post-title">{post.title}</h1>
          
          <div className="post-meta">
            <div className="post-category">
              <span className="category-badge">{post.category}</span>
            </div>
            <div className="meta-item">
              <Calendar className="meta-icon" />
              <span>{formatDate(post.created_at)}</span>
            </div>
            <div className="meta-item">
              <Eye className="meta-icon" />
              <span>{post.view_count} 조회</span>
            </div>
            <button onClick={handleShare} className="share-button">
              <Share2 className="share-icon" />
              공유
            </button>
          </div>

          {post.tags && post.tags.length > 0 && (
            <div className="post-tags">
              {post.tags.map((tag, index) => (
                <Link key={index} to={`/blog?tag=${encodeURIComponent(tag)}`} className="post-tag">
                  <Tag className="tag-icon" />
                  {tag}
                </Link>
              ))}
            </div>
          )}
        </header>

        {/* 블로그 글 내용 */}
        <article className="post-content">
          <div 
            className="content-body"
            dangerouslySetInnerHTML={{ __html: post.content }}
          />
        </article>

        {/* 관련 글 추천 (향후 구현) */}
        <section className="related-posts">
          <h3>관련 글</h3>
          <p>관련 글 기능은 추후 구현 예정입니다.</p>
        </section>

        {/* 하단 네비게이션 */}
        <div className="post-navigation">
          <button onClick={() => navigate('/blog')} className="nav-button">
            <ArrowLeft className="nav-icon" />
            블로그 목록으로 돌아가기
          </button>
        </div>
      </div>
    </div>
  );
};

export default BlogDetailPage;
