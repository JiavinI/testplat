# P0 只认证 MySQL 与 Playwright Chromium

P0 的 SQL 产品连接只支持 MySQL，并以 GF-04 的真实连接验收；PostgreSQL 保留数据库 Adapter 扩展位置，SQLite 只用于实现测试。Browser Worker 只认证固定构建的 Playwright Chromium 并默认无头运行，Firefox、WebKit 和系统 Chrome 后续按真实兼容性需求增加。这个范围优先保证首期真实链路的方言、类型、只读事务和浏览器行为可重复，而不是用未验收的驱动数量制造虚假兼容性。
