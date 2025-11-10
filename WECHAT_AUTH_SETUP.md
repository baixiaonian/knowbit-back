# 微信公众号登录功能配置说明

## 一、功能概述

实现了基于微信公众号的登录注册功能，用户通过扫码关注公众号并发送"666"获取验证码完成登录。

## 二、配置步骤

### 1. 环境变量配置

在 `.env` 文件中添加以下配置（或在 `app/core/config.py` 中直接设置）：

```env
# 微信公众号配置
WECHAT_APPID=你的公众号AppID
WECHAT_APPSECRET=你的公众号AppSecret
WECHAT_TOKEN=你的服务器配置Token（3-32位英文或数字）

# 可选：安全模式需要
WECHAT_ENCODING_AES_KEY=你的EncodingAESKey（43位字符）
```

### 2. 微信公众号后台配置

1. 登录[微信公众平台](https://mp.weixin.qq.com/)
2. 进入 **开发 -> 基本配置 -> 服务器配置**
3. 填写服务器配置：
   - **URL**: `https://your-domain.com/api/wechat/callback`
   - **Token**: 填写 `WECHAT_TOKEN` 的值
   - **EncodingAESKey**: 随机生成或使用 `WECHAT_ENCODING_AES_KEY`
   - **消息加解密方式**: 建议先选择 **明文模式**（开发阶段），生产环境使用 **安全模式**
4. 点击 **提交** 完成配置

### 3. 数据库

表已创建完成（`login_code` 表和 `user.wechat_openid` 字段）。

## 三、API接口说明

### 1. 微信回调接口（GET）
**路径**: `GET /api/wechat/callback`

微信服务器配置验证时调用，无需前端调用。

**参数**（Query参数）:
- `signature`: 微信签名
- `timestamp`: 时间戳
- `nonce`: 随机字符串
- `echostr`: 随机字符串

### 2. 微信回调接口（POST）
**路径**: `POST /api/wechat/callback`

接收微信消息和事件推送，处理用户发送的"666"消息。

### 3. 验证码验证接口
**路径**: `POST /api/auth/wechat/verify`

前端调用此接口验证用户输入的验证码。

**请求体**:
```json
{
  "code": "123456"
}
```

**成功响应**:
```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "username": null,
      "email": null,
      "phone": null,
      "avatar_url": null,
      "wechat_openid": "oXXXXXXXXXXXXX",
      "created_at": "2025-01-20T10:30:00"
    }
  }
}
```

**失败响应**:
```json
{
  "detail": "验证码无效或已过期"
}
```

## 四、使用流程

1. **前端显示公众号二维码**（普通关注二维码，可在微信公众平台获取）
2. **用户关注公众号**
3. **用户在公众号内发送 "666"**
4. **后端自动处理**：
   - 获取用户OpenID
   - 查询/创建用户
   - 生成6位验证码
   - 通过微信客服消息发送验证码给用户
5. **用户在前端登录页输入验证码**
6. **前端调用验证接口**：`POST /api/auth/wechat/verify`
7. **前端收到JWT token，完成登录**

## 五、前端示例代码

```javascript
// 1. 用户输入验证码后调用
async function verifyCode(code) {
  const response = await fetch('/api/auth/wechat/verify', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ code }),
  });
  
  if (response.ok) {
    const data = await response.json();
    // 保存token到localStorage或cookie
    localStorage.setItem('token', data.data.token);
    localStorage.setItem('user', JSON.stringify(data.data.user));
    // 跳转到主页面
    window.location.href = '/';
  } else {
    const error = await response.json();
    alert(error.detail || '验证码错误');
  }
}

// 2. 后续API调用时携带token
async function apiCall() {
  const token = localStorage.getItem('token');
  const response = await fetch('/api/some-endpoint', {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  // ...
}
```

## 六、注意事项

1. **验证码有效期**: 默认60秒，可在 `LOGIN_CODE_EXPIRE_SECONDS` 中配置
2. **同一用户限制**: 同一OpenID在有效期内只会有一个有效验证码，生成新验证码时旧验证码自动失效
3. **Access Token缓存**: 微信Access Token自动缓存，有效期2小时，提前5分钟刷新
4. **HTTPS要求**: 回调URL必须使用HTTPS（生产环境）
5. **消息模式**: 开发阶段建议使用明文模式，便于调试

## 七、故障排查

### 1. 签名验证失败
- 检查 `WECHAT_TOKEN` 配置是否正确
- 确认服务器时间是否准确

### 2. 无法获取验证码
- 检查公众号是否已关注
- 检查是否发送了"666"（严格匹配）
- 检查微信客服消息接口权限是否开通
- 查看后端日志确认错误信息

### 3. 验证码验证失败
- 确认验证码在有效期内（60秒）
- 确认验证码未被使用
- 检查数据库连接是否正常

### 4. Access Token获取失败
- 检查 `WECHAT_APPID` 和 `WECHAT_APPSECRET` 是否正确
- 确认公众号权限是否正常

## 八、安全建议

1. **生产环境配置**:
   - 使用环境变量存储敏感信息，不要硬编码
   - 使用安全模式的消息加解密
   - 配置合适的验证码有效期
   - 启用HTTPS

2. **防刷机制**（可选增强）:
   - 限制同一IP的请求频率
   - 限制同一OpenID的验证码生成频率
   - 记录异常登录尝试

3. **监控和日志**:
   - 记录验证码生成和使用情况
   - 监控异常登录尝试
   - 定期清理过期验证码数据

