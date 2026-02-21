# 青少年无人机大赛

基于 Flask + MySQL + Uniapp 的竞赛报名管理系统，支持学生端报名、管理员端数据导入和证书生成。

## 功能特性

### 后端功能
- ✅ **数据库模型设计**：完整的报名信息存储，支持多人项目
- ✅ **四级联动校验**：项目大类→具体任务→学段→人数的严格验证
- ✅ **敏感信息加密**：手机号和邮箱加密存储，脱敏显示
- ✅ **Excel导入功能**：支持参赛号和获奖信息批量导入，异常比对
- ✅ **PDF证书生成**：坐标居中渲染，字号自适应，支持多人项目
- ✅ **状态管理**：待审核、已通过、已拒绝状态控制

### 前端功能
- ✅ **动态表单**：根据项目选择自动渲染对应数量的选手输入框
- ✅ **行政区域联动**：市/区二级联动选择
- ✅ **实时校验**：手机号、邮箱格式验证
- ✅ **报名记录查询**：支持手机号查询个人报名状态
- ✅ **响应式设计**：适配小程序和H5

## 技术栈

### 后端
- **Flask**：Web框架
- **Flask-SQLAlchemy**：ORM数据库操作
- **Flask-Migrate**：数据库迁移
- **PyMySQL**：MySQL数据库驱动
- **cryptography**：数据加密
- **pandas + openpyxl**：Excel处理
- **reportlab**：PDF生成

### 前端
- **Uniapp**：跨平台开发框架
- **Vue.js**：前端框架
- **uView UI**：UI组件库（可选）

### 数据库
- **MySQL 5.7+**：主数据库

## 项目结构

```
project/
├── app.py                 # Flask主应用
├── models.py              # 数据库模型
├── routes.py              # 学生端API路由
├── admin_routes.py        # 管理员API路由
├── certificate_routes.py  # 证书生成API路由
├── certificate_generator.py # PDF证书生成器
├── config.py              # 配置文件
├── requirements.txt       # Python依赖
├── .env.example          # 环境变量示例
├── frontend/              # Uniapp前端
│   ├── pages/            # 页面文件
│   │   ├── index/        # 首页
│   │   ├── register/     # 报名页
│   │   ├── my-applications/ # 我的报名
│   │   └── success/      # 成功页
│   ├── utils/            # 工具函数
│   ├── pages.json        # 页面配置
│   └── manifest.json     # 应用配置
└── README.md             # 项目说明
```

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 数据库配置

```bash
# 创建MySQL数据库
mysql -u root -p
CREATE DATABASE competition_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 复制环境变量配置
cp .env.example .env

# 编辑.env文件，配置数据库连接
DATABASE_URL=mysql+pymysql://username:password@localhost/competition_db
```

### 3. 初始化数据库

```bash
# 初始化数据库迁移
flask db init

# 创建迁移文件
flask db migrate -m "Initial migration"

# 应用迁移
flask db upgrade
```

### 4. 启动后端服务

```bash
python app.py
```

后端服务将在 `http://localhost:5000` 启动

### 5. 前端开发

使用 HBuilderX 或 CLI 方式运行前端：

```bash
# CLI方式
npm install -g @dcloudio/uvm
uvm use latest
npm install -g @dcloudio/uni-cli
uni create frontend
cd frontend
npm run dev:mp-weixin  # 微信小程序
npm run dev:h5        # H5
```

## API文档

### 学生端接口

#### 1. 获取竞赛规则
```
GET /api/competition-rules
```

#### 2. 提交报名
```
POST /api/register
Content-Type: application/json

{
  "category": "无人机足球",
  "task": "5v5",
  "education_level": "中学",
  "participant_count": 5,
  "school_name": "测试学校",
  "contact_name": "张三",
  "contact_phone": "13800138000",
  "contact_email": "test@example.com",
  "participants": [
    {"participant_name": "选手1"},
    {"participant_name": "选手2"},
    {"participant_name": "选手3"},
    {"participant_name": "选手4"},
    {"participant_name": "选手5"}
  ]
}
```

#### 3. 查询我的报名
```
GET /api/my-applications?phone=13800138000
```

### 管理员接口

#### 1. 导入参赛号
```
POST /api/admin/import-match-no
Content-Type: multipart/form-data

file: Excel文件（包含：姓名、学校、参赛号）
```

#### 2. 导入获奖信息
```
POST /api/admin/import-awards
Content-Type: multipart/form-data

file: Excel文件（包含：参赛号、获奖等级）
```

#### 3. 生成证书
```
GET /api/certificate/generate/{application_id}
```

## 数据库设计

### 主要表结构

#### applications 表
- 存储报名基本信息
- 支持项目大类、具体任务、学段、人数
- 联系人信息加密存储
- 状态管理（待审核、已通过、已拒绝）

#### application_participants 表
- 存储选手信息
- 通过seq_no区分选手顺序
- 支持多人项目

#### certificate_templates 表
- 证书模板配置
- JSON格式存储坐标和样式

#### import_logs 表
- 导入日志记录
- 错误信息Base64编码存储

## 部署说明

### Docker部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "app.py"]
```

### 生产环境配置

1. 使用 Gunicorn 作为WSGI服务器
2. 配置 Nginx 反向代理
3. 使用 MySQL 主从复制
4. 配置 Redis 缓存

## 常见问题

### 1. 数据库连接失败
- 检查MySQL服务是否启动
- 确认数据库用户名密码正确
- 检查防火墙设置

### 2. 证书生成中文乱码
- 确保系统安装了中文字体
- 在certificate_generator.py中配置正确的字体路径

### 3. Excel导入失败
- 检查Excel文件格式（.xlsx）
- 确认必要的列存在
- 检查数据格式是否正确

## 开发规范

### 代码规范
- 遵循PEP 8 Python编码规范
- 使用ESLint进行前端代码检查
- 提交前运行测试用例

### API设计
- RESTful API设计
- 统一的错误处理
- 完整的参数验证

### 数据库设计
- 合理的索引设计
- 外键约束
- 数据完整性检查

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交代码
4. 创建 Pull Request

## 许可证

MIT License

## 联系方式

如有问题，请提交 Issue 或联系开发团队。
