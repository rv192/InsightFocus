-- InsightFocus 数据库初始化脚本
-- 创建日期: 2024-07-22
-- 最后更新: 2024-07-22
-- 描述: 这个脚本创建了InsightFocus数据库及其所有相关表。
--       它设置了文章、用户、RSS源、标签等实体的基本结构。

-- 创建数据库
CREATE DATABASE IF NOT EXISTS InsightFocus;
USE InsightFocus;

-- 创建类别表
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT
);

-- 创建用户表
CREATE TABLE IF NOT EXISTS rssUsers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    created_at DATETIME,
    last_login_at DATETIME,
    UNIQUE KEY (email)
);

-- 创建RSS源表
CREATE TABLE IF NOT EXISTS rssSources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    url VARCHAR(2083) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    last_fetched_at DATETIME
);

-- 创建文章表
CREATE TABLE IF NOT EXISTS articles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    guid CHAR(36),
    source_id INT NOT NULL,
    category_id INT,
    url VARCHAR(2083) NOT NULL,
    url_hash VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    plain_content TEXT,
    content_hash VARCHAR(64),
    published_at DATETIME,
    fetched_at DATETIME,
    summary TEXT,
    language VARCHAR(50),
    read_time INT,
    last_updated_at DATETIME,
    UNIQUE KEY (url_hash),
    FOREIGN KEY (source_id) REFERENCES rssSources(id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- 创建用户-RSS源关联表
CREATE TABLE IF NOT EXISTS userRssSources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    source_id INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES rssUsers(id),
    FOREIGN KEY (source_id) REFERENCES rssSources(id)
);

-- 创建用户关注点表
CREATE TABLE IF NOT EXISTS userFocuses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    type ENUM('tag', 'content') NOT NULL,
    content TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES rssUsers(id)
);

-- 创建关注内容表
CREATE TABLE IF NOT EXISTS focusedContents (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    article_id BIGINT NOT NULL,
    focus_id INT NOT NULL,
    created_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES rssUsers(id),
    FOREIGN KEY (article_id) REFERENCES articles(id),
    FOREIGN KEY (focus_id) REFERENCES userFocuses(id)
);

-- 创建用户文章状态表
CREATE TABLE IF NOT EXISTS userArticleStatus (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    article_id BIGINT NOT NULL,
    status ENUM('unread', 'read', 'read_later') NOT NULL,
    updated_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES rssUsers(id),
    FOREIGN KEY (article_id) REFERENCES articles(id)
);

-- 创建标签表
CREATE TABLE IF NOT EXISTS tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    UNIQUE KEY (name)
);

-- 创建文章-标签关联表
CREATE TABLE IF NOT EXISTS article_tags (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    article_id BIGINT NOT NULL,
    tag_id INT NOT NULL,
    FOREIGN KEY (article_id) REFERENCES articles(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);

-- 插入类别数据
INSERT INTO categories (name, description) VALUES
('新闻与时事', '包括政治、经济、国际关系和社会事件等'),
('科技与创新', '涵盖信息技术、人工智能、生物科技和航空航天等领域'),
('商业与金融', '关于市场动态、创业、投资和公司新闻'),
('健康与医疗', '包括医学研究、公共卫生、心理健康和营养饮食'),
('环境与可持续发展', '涉及气候变化、可再生能源、生态保护等主题'),
('文化与艺术', '包括文学、视觉艺术、音乐、电影与电视'),
('教育与学术', '关于教育政策、学术研究、在线学习和终身教育'),
('体育与娱乐', '涵盖体育赛事、娱乐新闻、游戏产业和休闲活动'),
('生活方式', '包括旅游、美食、时尚和家居等话题'),
('科学与探索', '涉及物理学、天文学、地球科学和考古学等领域'),
('社会问题', '关注人权、社会正义、平等与多样性等议题'),
('历史与观点', '包括历史事件、评论分析、观点文章和未来预测');