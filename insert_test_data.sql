-- 테스트 데이터 삽입
INSERT INTO orders (id, user_id, user_email, platform, service, link, quantity, price, status, total_amount, smmkings_cost) 
VALUES ('test1', 'user1', 'user1@example.com', 'instagram', 'followers', 'https://instagram.com/test', 1000, 50000, 'completed', 50000, 40000);

INSERT INTO orders (id, user_id, user_email, platform, service, link, quantity, price, status, total_amount, smmkings_cost) 
VALUES ('test2', 'user2', 'user2@example.com', 'youtube', 'subscribers', 'https://youtube.com/test', 500, 30000, 'completed', 30000, 24000);

INSERT INTO orders (id, user_id, user_email, platform, service, link, quantity, price, status, total_amount, smmkings_cost) 
VALUES ('test3', 'user3', 'user3@example.com', 'tiktok', 'followers', 'https://tiktok.com/test', 2000, 75000, 'completed', 75000, 60000);

INSERT INTO orders (id, user_id, user_email, platform, service, link, quantity, price, status, total_amount, smmkings_cost) 
VALUES ('test4', 'user4', 'user4@example.com', 'instagram', 'likes', 'https://instagram.com/test', 500, 25000, 'cancelled', 25000, 20000);
