/* ========================================================================
   OPTIMIZED DATABASE SCHEMA FOR SNSPMT
   ======================================================================== */

CREATE DATABASE IF NOT EXISTS snspmt
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE snspmt;

/* ========================================================================
   1) USERS & POINTS
   ======================================================================== */

CREATE TABLE users (
  user_id        VARCHAR(255) PRIMARY KEY,  -- Firebase UID (문자열 유지)
  email          VARCHAR(255) NOT NULL UNIQUE,
  name           VARCHAR(120) NULL,
  display_name   VARCHAR(120) NULL,
  google_id      VARCHAR(255) NULL UNIQUE,
  kakao_id       VARCHAR(255) NULL UNIQUE,
  profile_image  TEXT NULL,
  last_login     DATETIME NULL,
  last_activity  DATETIME NULL,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_users_email (email),
  INDEX idx_users_google (google_id),
  INDEX idx_users_kakao (kakao_id)
) ENGINE=InnoDB;

CREATE TABLE points (
  user_id     VARCHAR(255) PRIMARY KEY,
  points      BIGINT NOT NULL DEFAULT 0,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_points_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT ck_points_nonneg CHECK (points >= 0)
) ENGINE=InnoDB;

CREATE TABLE point_purchases (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  purchase_id     VARCHAR(255) NULL UNIQUE,
  user_id         VARCHAR(255) NOT NULL,
  user_email      VARCHAR(255) NULL,
  amount          INT NOT NULL,                -- points amount
  price           DECIMAL(10,2) NOT NULL,      -- payment amount
  status          ENUM('pending','kcp_registered','approved','rejected') NOT NULL DEFAULT 'pending',
  depositor_name  VARCHAR(255) NULL,
  buyer_name      VARCHAR(255) NULL,
  bank_name       VARCHAR(255) NULL,
  bank_info       TEXT NULL,
  receipt_type    VARCHAR(50) NULL,
  business_info   TEXT NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_point_purchases_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT ck_point_purchase CHECK (amount > 0 AND price >= 0),
  INDEX idx_point_purchases_user (user_id),
  INDEX idx_point_purchases_status (status),
  INDEX idx_point_purchases_created (created_at)
) ENGINE=InnoDB;

/* ========================================================================
   2) SERVICES (PRODUCT CATALOG)
   ======================================================================== */

CREATE TABLE services (
  service_id       BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  category         VARCHAR(120) NULL,
  service_name     VARCHAR(255) NOT NULL,
  platform         VARCHAR(80)  NOT NULL,        -- Instagram, TikTok, YouTube, ...
  min_quantity     INT NOT NULL DEFAULT 1,
  max_quantity     INT NOT NULL,
  unit_price       DECIMAL(10,2) NOT NULL,
  is_international TINYINT(1) NOT NULL DEFAULT 1,
  is_active        TINYINT(1) NOT NULL DEFAULT 1,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT ck_services_qty   CHECK (min_quantity > 0 AND max_quantity >= min_quantity),
  CONSTRAINT ck_services_price CHECK (unit_price >= 0),
  INDEX idx_services_platform (platform),
  INDEX idx_services_active (is_active)
) ENGINE=InnoDB;

/* ========================================================================
   3) ORDERS (HEADER + ITEMS)
   ======================================================================== */

CREATE TABLE orders (
  order_id           VARCHAR(255) PRIMARY KEY,  -- SMM Panel 주문 ID 또는 타임스탬프 기반
  user_id            VARCHAR(255) NOT NULL,
  user_email         VARCHAR(255) NULL,
  status             ENUM('pending','running','completed','failed','cancelled','scheduled','package_processing') NOT NULL DEFAULT 'pending',
  referral_code      VARCHAR(50) NULL,
  discount_amount    DECIMAL(10,2) NOT NULL DEFAULT 0,
  total_price        DECIMAL(10,2) NOT NULL DEFAULT 0,
  external_order_id  VARCHAR(255) NULL,
  smm_panel_order_id VARCHAR(255) NULL,
  remarks            TEXT NULL,
  comments           TEXT NULL,
  last_status_check  DATETIME NULL,
  is_scheduled       TINYINT(1) NOT NULL DEFAULT 0,
  scheduled_datetime DATETIME NULL,
  package_steps      JSON NULL,              -- 패키지 단계 정보 (JSON)
  package_start_at   DATETIME NULL,          -- 패키지 시작 시간
  detailed_service   TEXT NULL,
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT ck_orders_amounts CHECK (discount_amount >= 0 AND total_price >= 0),
  INDEX idx_orders_user (user_id),
  INDEX idx_orders_status (status),
  INDEX idx_orders_created (created_at),
  INDEX idx_orders_user_created (user_id, created_at DESC),
  INDEX idx_orders_scheduled (is_scheduled, scheduled_datetime)
) ENGINE=InnoDB;

CREATE TABLE order_items (
  order_item_id          BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  order_id               VARCHAR(255) NOT NULL,
  service_id             VARCHAR(255) NOT NULL,  -- SMM Panel 서비스 ID
  link                   TEXT NOT NULL,           -- target link
  quantity               INT NOT NULL,
  unit_price             DECIMAL(10,2) NOT NULL,
  amount                 DECIMAL(10,2) GENERATED ALWAYS AS (ROUND(unit_price * quantity, 2)) STORED,
  service_name_snapshot  VARCHAR(255) NULL,
  platform_snapshot      VARCHAR(80)  NULL,
  comments               TEXT NULL,
  created_at             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
  CONSTRAINT ck_order_item CHECK (quantity > 0 AND unit_price >= 0),
  INDEX idx_order_items_order (order_id),
  INDEX idx_order_items_service (service_id)
) ENGINE=InnoDB;

/* keep orders.total_price synced with order_items.amount */
DELIMITER $$

CREATE TRIGGER trg_order_items_ai AFTER INSERT ON order_items
FOR EACH ROW
BEGIN
  UPDATE orders
     SET total_price = (SELECT IFNULL(SUM(amount),0) FROM order_items WHERE order_id = NEW.order_id)
   WHERE order_id = NEW.order_id;
END$$

CREATE TRIGGER trg_order_items_au AFTER UPDATE ON order_items
FOR EACH ROW
BEGIN
  UPDATE orders
     SET total_price = (SELECT IFNULL(SUM(amount),0) FROM order_items WHERE order_id = NEW.order_id)
   WHERE order_id = NEW.order_id;
END$$

CREATE TRIGGER trg_order_items_ad AFTER DELETE ON order_items
FOR EACH ROW
BEGIN
  UPDATE orders
     SET total_price = (SELECT IFNULL(SUM(amount),0) FROM order_items WHERE order_id = OLD.order_id)
   WHERE order_id = OLD.order_id;
END$$

DELIMITER ;

/* ========================================================================
   4) EXECUTION_PROGRESS (UNIFIED SCHEDULE/SPLIT/PACKAGE)
   ======================================================================== */

CREATE TABLE execution_progress (
  exec_id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  order_id           VARCHAR(255) NOT NULL,
  exec_type          ENUM('split','package') NOT NULL,     -- package만 사용 (split은 제거됨)
  step_number        INT NOT NULL,                         -- package step index
  step_name          VARCHAR(255) NULL,                    -- when package
  service_id         VARCHAR(255) NULL,                    -- package step service
  quantity           INT NULL,
  scheduled_datetime DATETIME NULL,                        -- schedule (24시간 후 등)
  priority           TINYINT UNSIGNED NOT NULL DEFAULT 5,  -- 1 = highest
  lock_token         VARCHAR(64) NULL,                     -- worker locking
  retry_count        INT NOT NULL DEFAULT 0,
  last_error_at      DATETIME NULL,
  status             ENUM('pending','running','completed','failed','skipped','scheduled') NOT NULL DEFAULT 'pending',
  smm_panel_order_id VARCHAR(255) NULL,
  error_message      TEXT NULL,
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at       DATETIME NULL,
  failed_at          DATETIME NULL,
  CONSTRAINT fk_exec_order FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
  CONSTRAINT ck_exec_qty CHECK (quantity IS NULL OR quantity >= 0),
  UNIQUE KEY uq_exec (order_id, exec_type, step_number),    -- prevent duplicates
  INDEX idx_exec_key (order_id, exec_type, step_number),
  INDEX idx_exec_status_time (status, scheduled_datetime),
  INDEX idx_exec_status_time_prio (status, scheduled_datetime, priority),
  INDEX idx_exec_lock (lock_token)
) ENGINE=InnoDB;

/* ========================================================================
   5) REFERRALS / COMMISSION (UNIFIED LEDGER)
   ======================================================================== */

CREATE TABLE referral_codes (
  id               BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  code             VARCHAR(50)
                      CHARACTER SET utf8mb4
                      COLLATE utf8mb4_0900_as_cs           -- case-sensitive
                      NOT NULL,
  user_id          VARCHAR(255) NOT NULL,                  -- owner (referrer)
  user_email       VARCHAR(255) NULL,
  name             VARCHAR(255) NULL,
  phone            VARCHAR(255) NULL,
  is_active        TINYINT(1) NOT NULL DEFAULT 1,
  usage_count      INT NOT NULL DEFAULT 0,
  total_commission DECIMAL(10,2) NOT NULL DEFAULT 0,       -- synced by triggers
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_referral_code UNIQUE (code),
  CONSTRAINT fk_referral_codes_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  INDEX idx_referral_codes_user (user_id),
  INDEX idx_referral_codes_active (is_active)
) ENGINE=InnoDB;

CREATE TABLE commission_ledger (
  ledger_id         BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  referral_code     VARCHAR(50) NOT NULL,          -- FK → referral_codes(code)
  referrer_user_id  VARCHAR(255) NOT NULL,         -- owner
  referred_user_id  VARCHAR(255) NULL,             -- invitee (if any)
  order_id          VARCHAR(255) NULL,              -- related order (if any)
  event             ENUM('earn','payout','adjust','reverse') NOT NULL,
  base_amount       DECIMAL(10,2) NULL,            -- for 'earn'
  commission_rate   DECIMAL(5,4)  NULL,            -- for 'earn' (e.g., 0.1000)
  amount            DECIMAL(10,2) NOT NULL,        -- +credit / -debit
  status            ENUM('pending','confirmed','cancelled') NOT NULL DEFAULT 'confirmed',
  notes             TEXT NULL,
  external_ref      VARCHAR(100) NULL,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  confirmed_at      DATETIME NULL,
  CONSTRAINT fk_ledger_code    FOREIGN KEY (referral_code)    REFERENCES referral_codes(code),
  CONSTRAINT fk_ledger_owner   FOREIGN KEY (referrer_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT fk_ledger_refer   FOREIGN KEY (referred_user_id) REFERENCES users(user_id),
  CONSTRAINT fk_ledger_order   FOREIGN KEY (order_id)         REFERENCES orders(order_id),
  INDEX idx_ledger_code_time (referral_code, created_at),
  INDEX idx_ledger_owner_time (referrer_user_id, created_at),
  INDEX idx_ledger_event_time (event, created_at),
  INDEX idx_ledger_order (order_id)
) ENGINE=InnoDB;

/* enforce orders.referral_code integrity */
ALTER TABLE orders
  ADD CONSTRAINT fk_orders_referral_code
  FOREIGN KEY (referral_code) REFERENCES referral_codes(code);

/* auto-sync referral_codes.total_commission from commission_ledger */
DELIMITER $$

CREATE TRIGGER trg_commission_ai AFTER INSERT ON commission_ledger
FOR EACH ROW
BEGIN
  UPDATE referral_codes
     SET total_commission = (
       SELECT IFNULL(SUM(amount),0)
       FROM commission_ledger
       WHERE referral_code = NEW.referral_code
         AND status='confirmed'
     )
   WHERE code = NEW.referral_code;
END$$

CREATE TRIGGER trg_commission_au AFTER UPDATE ON commission_ledger
FOR EACH ROW
BEGIN
  UPDATE referral_codes
     SET total_commission = (
       SELECT IFNULL(SUM(amount),0)
       FROM commission_ledger
       WHERE referral_code = NEW.referral_code
         AND status='confirmed'
     )
   WHERE code = NEW.referral_code;

  IF OLD.referral_code <> NEW.referral_code THEN
    UPDATE referral_codes
       SET total_commission = (
         SELECT IFNULL(SUM(amount),0)
         FROM commission_ledger
         WHERE referral_code = OLD.referral_code
           AND status='confirmed'
       )
     WHERE code = OLD.referral_code;
  END IF;
END$$

CREATE TRIGGER trg_commission_ad AFTER DELETE ON commission_ledger
FOR EACH ROW
BEGIN
  UPDATE referral_codes
     SET total_commission = (
       SELECT IFNULL(SUM(amount),0)
       FROM commission_ledger
       WHERE referral_code = OLD.referral_code
         AND status='confirmed'
     )
   WHERE code = OLD.referral_code;
END$$

DELIMITER ;

/* ========================================================================
   6) OPTIONAL OPS (COUPONS / NOTICES / BLOG_POSTS)
   ======================================================================== */

CREATE TABLE coupons (
  id             BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id        VARCHAR(255) NOT NULL,
  referral_code  VARCHAR(50) NULL,
  discount_type  ENUM('percentage','fixed') NOT NULL DEFAULT 'percentage',
  discount_value DECIMAL(5,2) NOT NULL,
  is_used        TINYINT(1) NOT NULL DEFAULT 0,
  used_at        DATETIME NULL,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at     DATETIME NULL,
  CONSTRAINT fk_coupons_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT ck_coupon_value CHECK (discount_value >= 0),
  INDEX idx_coupons_user (user_id),
  INDEX idx_coupons_used (is_used),
  INDEX idx_coupons_expires (expires_at)
) ENGINE=InnoDB;

CREATE TABLE notices (
  id          BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  title       VARCHAR(255) NOT NULL,
  content     TEXT NOT NULL,
  image_url   VARCHAR(500) NULL,
  is_active   TINYINT(1) NOT NULL DEFAULT 1,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_notices_active (is_active)
) ENGINE=InnoDB;

CREATE TABLE blog_posts (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  title         VARCHAR(255) NOT NULL,
  content       TEXT NOT NULL,
  excerpt       TEXT NULL,
  category      VARCHAR(100) NULL,
  thumbnail_url TEXT NULL,
  tags          JSON NULL,
  is_published  TINYINT(1) NOT NULL DEFAULT 0,
  view_count    INT NOT NULL DEFAULT 0,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_blog_published (is_published),
  INDEX idx_blog_category (category),
  INDEX idx_blog_created (created_at)
) ENGINE=InnoDB;

/* ========================================================================
   7) VIEWS (FOR REPORTING)
   ======================================================================== */

CREATE OR REPLACE VIEW commission_balance_view AS
SELECT referrer_user_id, SUM(amount) AS current_balance
FROM commission_ledger
WHERE status='confirmed'
GROUP BY referrer_user_id;

CREATE OR REPLACE VIEW orders_summary_view AS
SELECT
  o.order_id,
  o.user_id,
  o.status,
  o.total_price,
  COUNT(oi.order_item_id) AS line_count,
  SUM(oi.quantity)        AS total_quantity,
  MIN(oi.created_at)      AS first_line_at
FROM orders o
LEFT JOIN order_items oi ON oi.order_id = o.order_id
GROUP BY o.order_id, o.user_id, o.status, o.total_price;

/* ========================================================================
   8) STORED PROCEDURES (PACKAGE EXPANSION)
   ======================================================================== */

DELIMITER $$

CREATE PROCEDURE sp_expand_package(
  IN p_order_id VARCHAR(255),
  IN p_start_at DATETIME,
  IN p_steps_json JSON
)
BEGIN
  DECLARE i INT DEFAULT 0;
  DECLARE n INT;
  DECLARE step_offset INT;
  DECLARE step_delay INT;
  
  SET n = JSON_LENGTH(p_steps_json);
  
  WHILE i < n DO
    -- delay를 offset_minutes로 변환 (누적)
    SET step_delay = JSON_EXTRACT(p_steps_json, CONCAT('$[', i, '].delay'));
    IF step_delay IS NULL THEN
      SET step_delay = 1440;  -- 기본값: 24시간 (분 단위)
    END IF;
    
    -- 첫 번째 단계는 0분, 이후 단계는 이전 단계들의 delay 합계
    IF i = 0 THEN
      SET step_offset = 0;
    ELSE
      -- 이전 단계들의 delay 합계 계산
      SET step_offset = (
        SELECT IFNULL(SUM(JSON_EXTRACT(p_steps_json, CONCAT('$[', j, '].delay'))), 0)
        FROM (SELECT @j := j FROM (SELECT 0 as j UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10 UNION SELECT 11 UNION SELECT 12 UNION SELECT 13 UNION SELECT 14 UNION SELECT 15 UNION SELECT 16 UNION SELECT 17 UNION SELECT 18 UNION SELECT 19 UNION SELECT 20 UNION SELECT 21 UNION SELECT 22 UNION SELECT 23 UNION SELECT 24 UNION SELECT 25 UNION SELECT 26 UNION SELECT 27 UNION SELECT 28 UNION SELECT 29) AS numbers WHERE j < i) AS prev_steps
      );
    END IF;
    
    INSERT INTO execution_progress
      (order_id, exec_type, step_number, step_name, service_id, quantity, scheduled_datetime, status)
    VALUES
      (
        p_order_id,
        'package',
        i + 1,  -- step_number는 1부터 시작
        JSON_UNQUOTE(JSON_EXTRACT(p_steps_json, CONCAT('$[', i, '].name'))),
        CAST(JSON_EXTRACT(p_steps_json, CONCAT('$[', i, '].id')) AS CHAR),
        JSON_EXTRACT(p_steps_json, CONCAT('$[', i, '].quantity')),
        DATE_ADD(p_start_at, INTERVAL step_offset MINUTE),
        'pending'
      )
    ON DUPLICATE KEY UPDATE
      step_name=VALUES(step_name),
      service_id=VALUES(service_id),
      quantity=VALUES(quantity),
      scheduled_datetime=VALUES(scheduled_datetime);
    
    SET i = i + 1;
  END WHILE;
END$$

DELIMITER ;

/* ========================================================================
   END OF SCHEMA
   ======================================================================== */

