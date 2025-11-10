# 微信公众号登录原理与实现方案

## 1. 功能概述
- **目标**：允许网页端用户通过微信公众号完成身份认证与登录。
- **关键特性**：
  - 无需输入账号密码。
  - 微信端发送关键字自动获取验证码。
  - 验证成功后返回 JWT token，前端使用 token 调用受保护接口。
- **适用场景**：企业内部工具、活动扫码登录、小程序 H5 扫码登录等。

## 2. 整体链路
1. **二维码展示**：前端展示公众号二维码，提示用户关注并发送“666”。
2. **用户发送关键字**：用户在微信对话框输入“666”。
3. **微信服务器回调**：微信将该消息推送到后端 `POST /api/wechat/callback`。
4. **后端处理消息**：
   - 验证签名，确保请求来自微信。
   - 解析 XML，提取 OpenID 与消息内容。
   - 生成 6 位验证码，写入数据库。
   - 直接以被动回复的方式返回验证码文案。
5. **用户收到验证码**：微信端立即收到 “您的登录验证码：xxxxxx，请在1分钟内使用”。
6. **前端提交验证码**：网页端调用 `POST /api/auth/wechat/verify` 完成校验。
7. **后端验证**：
   - 检查验证码是否存在、未使用且在有效期内。
   - 若用户首次登录则自动创建用户并绑定 OpenID。
   - 生成 JWT token 并返回用户信息。
8. **会话建立**：前端保存 token（本地存储或 Cookie），后续请求在 `Authorization` 头中携带。

## 3. 关键组件与文件
| 模块 | 路径 | 职责 | 备注 |
|------|------|------|------|
| 配置 | `app/core/config.py` | 统一管理 App、DB、JWT、微信配置 | 通过 `BaseSettings` 自动加载 `.env` |
| DB 模型 | `app/models/user.py` | 新增 `wechat_openid` 字段 | 绑定用户与 OpenID |
| DB 模型 | `app/models/login_code.py` | 存储验证码信息 | 记录 `openid`、验证码、过期时间、使用状态 |
| 微信签名工具 | `app/utils/wechat_signature.py` | 校验微信回调请求合法性 | 使用 SHA1(token, timestamp, nonce) |
| Auth 工具 | `app/utils/auth.py` | JWT 生成与解析、兼容旧接口 | `SECRET_KEY` 必须手动配置 |
| 微信服务 | `app/services/wechat_service.py` | Access Token 管理（备用） | 当前主动客服消息已停用 |
| Auth 服务 | `app/services/auth_service.py` | 验证码生成、用户创建/查询 | 返回验证码供被动回复使用 |
| API 路由 | `app/api/wechat_auth.py` | 处理微信回调、验证码验证 | 包含 GET/POST 回调与验证码校验 | 
| 文档 | `api.md` & `WECHAT_AUTH_SETUP.md` | 接口说明、配置指引 | 供前后端调用与部署参考 |

## 4. 数据库设计
- **用户表 `public.user`**
  - 新增字段：`wechat_openid VARCHAR(64) UNIQUE`
  - 建立索引 `idx_user_openid`
- **验证码表 `public.login_code`**
  - 字段：`openid`、`verification_code`、`expire_at`、`used`、`user_id`
  - 逻辑：同一 OpenID 新验证码会覆盖旧记录；验证码默认有效期 60 秒。

SQL 片段：
```sql
ALTER TABLE public.user ADD COLUMN wechat_openid VARCHAR(64) UNIQUE;

CREATE TABLE public.login_code (
    id BIGSERIAL PRIMARY KEY,
    openid VARCHAR(64) NOT NULL,
    verification_code VARCHAR(6) NOT NULL,
    expire_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    user_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES public.user(id)
);
```

## 5. 关键流程说明
### 5.1 微信消息回调
```sequence
WeChat -> Callback API: POST /api/wechat/callback
Callback API -> Signature Util: verify_signature(token, timestamp, nonce)
Signature Util -> Callback API: 校验结果
Callback API -> DB: AuthService.create_login_code(openid)
DB --> Callback API: 验证码
Callback API --> WeChat: XML 被动回复验证码
```

- 使用被动回复（返回 XML）避免客服消息接口 `48001` 权限问题。
- 支持明文消息模式，无需 EncodingAESKey。
- 回调接口还处理 GET 请求，用于首次服务器校验（返回 `echostr`）。

### 5.2 验证码验证
```sequence
Frontend -> Backend: POST /api/auth/wechat/verify (code)
Backend -> DB: 查询 login_code
DB --> Backend: 验证码记录
Backend -> Backend: AuthService.verify_login_code
Backend -> JWT Util: create_access_token
JWT Util --> Backend: token
Backend --> Frontend: { token, user }
```

- 通过 `AuthService.verify_login_code` 确认验证码有效性并标记 `used = TRUE`。
- 调用 `create_access_token` 写入 `sub`（用户 ID）和 `openid`。
- 返回 `ResponseModel` 包含 token 与用户信息。

## 6. 配置与部署要点
| 项 | 说明 | 配置位置 |
|----|------|----------|
| 微信服务器 URL | `https://{domain}/api/wechat/callback` | 微信公众平台后台 |
| 微信 Token | `WECHAT_TOKEN` | `.env` + 微信后台保持一致 |
| AppID/Secret | `WECHAT_APPID` / `WECHAT_APPSECRET` | `.env`（需手动配置） |
| EncodingAESKey | `WECHAT_ENCODING_AES_KEY` | 明文模式可留空 |
| JWT 密钥 | `SECRET_KEY` | `.env` 自定义随机字符串 |
| 验证码时长 | `LOGIN_CODE_EXPIRE_SECONDS` (默认 60s) | `.env` | 
| DEBUG 模式 | `DEBUG=True`（开发） | `.env` | 

**注意**：`.env` 修改后需重启服务才能生效。

## 7. 安全与限制
- **签名验证**：所有微信回调必须通过 `verify_signature`
- **验证码有效期**：默认 60 秒，过期或已使用会返回 400
- **调试兼容**：`get_current_user_id` 在 `DEBUG=True` 时允许无 token 访问（返回用户 ID 1）<br>生产环境应关闭 DEBUG 并强制使用 JWT。
- **IP 白名单**：若后续改回客服消息方式，需要在微信后台配置服务器出口 IP 白名单。
- **日志记录**：关键流程会打印异常日志，便于排查（如签名失败、验证码生成失败）。

## 8. 本地/线上测试建议
1. 在微信公众平台开启服务器配置（明文模式）。
2. 启动后端服务，确认 `/api/wechat/callback` 可访问。
3. 关注公众号，发送“666”，检查后台日志是否生成验证码并被动回复。
4. 使用 Postman/前端调用 `POST /api/auth/wechat/verify` 验证逻辑。
5. 携带返回的 token 访问其他受保护接口，确认鉴权正常。

## 9. 可扩展方向
- 支持自定义验证码长度、模板信息。
- 增加二维码与 OpenID 场景值绑定（带参数二维码）。
- 接入微信群发、模板消息等高级能力（需额外权限）。
- 结合 WebSocket 实时通知前端验证码状态。
- 加入防刷策略（IP/频率限制、图形验证码）。

---
如需查看接口参数与报文示例，请参考 `api.md`；部署时请依照 `WECHAT_AUTH_SETUP.md` 配置。
