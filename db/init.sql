-- InsightFocus 数据库初始化脚本
-- 创建日期: 2024-07-22
-- 最后更新: 2024-07-22
-- 描述: 这个脚本创建了InsightFocus数据库及其所有相关表。
--       它设置了文章、用户、RSS源、标签等实体的基本结构。

-- 创建数据库
CREATE DATABASE IF NOT EXISTS InsightFocus;
USE InsightFocus;

-- 创建主题表
CREATE TABLE IF NOT EXISTS topics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT
);

-- 创建体裁分类表
CREATE TABLE IF NOT EXISTS genres (
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
    genre_id INT,
    topic_id INT,
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
    FOREIGN KEY (genre_id) REFERENCES genres(id),
    FOREIGN KEY (topic_id) REFERENCES topics(id)
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

INSERT INTO topics (id, name, description) VALUES
(1, '时事政治', '关注国内外政治、经济、社会等重大事件'),
(2, '商业财经', '涵盖商业活动、金融市场、经济趋势等方面'),
(3, '科技', '报道最新科技发展、科学发现、技术创新等'),
(4, '科学', '探讨自然科学领域的知识、研究和发现'),
(5, '健康', '关注身心健康、疾病预防、医疗保健等'),
(6, '环境', '探讨环境保护、气候变化、生态平衡等议题'),
(7, '文化', '涉及文化艺术、传统习俗、价值观念等方面'),
(8, '艺术', '涵盖音乐、绘画、雕塑、电影等艺术形式'),
(9, '体育', '报道各类体育赛事、运动员、体育文化等'),
(10, '娱乐', '关注电影、音乐、游戏等娱乐产业'),
(11, '生活方式', '探讨生活方式、时尚潮流、消费趋势等'),
(12, '旅游', '分享旅游攻略、目的地推荐、旅行体验等'),
(13, '教育', '关注教育政策、学习方法、学校生活等'),
(14, '历史', '回顾历史事件、人物传记、文化遗产等'),
(15, '社会', '探讨社会现象、民生问题、社会发展等'),
(16, '技术', '侧重于具体的技术应用、技能和讨论，例如编程、软件开发等'),
(0, '其他', '不易归类于以上主题的内容');

INSERT INTO genres (id, name, description) VALUES
(1, '新闻报道', '客观报道时事，强调及时性和真实性'),
(2, '评论分析', '对事件、现象表达观点和分析，主观性较强'),
(3, '专题报道/特写', '深入探讨特定主题，兼具报道和分析的特点，篇幅较长'),
(4, '调查报道', '针对特定事件或问题进行深入调查和揭露'),
(5, '学术论文', '基于原创研究，遵循学术规范，旨在传播学术成果'),
(6, '科普文章', '以通俗易懂的方式介绍科学知识'),
(7, '文学作品', '小说、诗歌、戏剧等虚构类作品'),
(8, '非虚构作品', '传记、回忆录、历史等基于真实事件的作品'),
(9, '指南教程', '提供实用性指导，例如操作指南、学习教程等'),
(10, '访谈', '以问答形式呈现人物观点和经历'),
(11, '评论', '对书籍、电影、产品等进行评价'),
(12, '博客文章', '个人或机构发布的观点、经验分享等'),
(13, '多媒体内容', '以视频、音频、图片等为主，或结合多种媒体形式呈现的文章'),
(0, '其他', '不易归类于以上类型的文章');

-- 在rssSources表插入测试数据
INSERT INTO rssSources (url, name, description) VALUES
('https://36kr.com/feed', '36氪-RSS', '36氪是一个关注互联网创业的科技博客。');

-- 在rssUsers表插入测试数据
INSERT INTO rssUsers (username, email, created_at, last_login_at) VALUES
('guest', 'test@mail.com', NOW(), NOW());

-- 在userFocuses表插入测试数据
INSERT INTO userFocuses (user_id, content) VALUES
(1, '我是一个程序员，我也炒A股和炒币。关注大模型等AI技术，也关心中美关系博弈以及中东局势和俄乌冲突。');