# GLaDOS 自动签到

使用 GitHub Actions 定时调用 https://glados.cloud/api/user/checkin ，支持 gld:（新版）和 koa:（旧版）Cookie，以及邮件通知和两个账号的独立定时任务。

## 配置 Cookie

1. 登录 https://glados.cloud ，在浏览器开发者工具（F12）里找到 Application / Storage → Cookies → glados.cloud。
2. 复制完整 Cookie（可以从 Network 的请求头中复制整段 Cookie:），确保会话字段成对出现：

   gld:sess=xxxxxx; gld:sess.sig=yyyyyy

   旧版 Cookie 也支持：

   koa:sess=xxxxxx; koa:sess.sig=yyyyyy

3. 在本仓库 Settings → Secrets and variables → Actions → Repository secrets 中为两个账号分别设置 GLADOS_COOKIE_321018142、GLADOS_COOKIE_545443766，粘贴各自的原始 Cookie。
4. 在 Actions 页面手动运行对应的 check_in_321018142 或 check_in_545443766 工作流进行验证。

**注意：** 不要将 gld: 手工替换为 koa:，也不要只复制 sess 而漏掉 sess.sig。脚本原样发送 Cookie；格式校验只能判断字段是否成对，**无法判断会话是否已过期**。如果返回「没有权限」（例如 Code: -2），请重新登录获取 Cookie，更新对应的 Secret。

## 其他配置

- GLADOS_TOKEN（可选）：签到 Token，未设置时默认为 glados.cloud。
- MAIL_USERNAME、MAIL_PASSWORD：邮件通知所需账号和凭据（可选）。
- MAIL_TO：收件地址，默认等于发件地址。
- MAIL_SMTP_SERVER：默认 smtp.qq.com。
- MAIL_SMTP_PORT：默认 465。
- REQUESTS_TIMEOUT：请求超时秒数，默认 10。

两个 workflow 分别读取原有 Secrets，不需要改工作流配置；邮件凭据也保持原有方式。签到成功或已签到时退出码为 0；Cookie 格式错误、鉴权失败、请求异常等会返回非零退出码，使 GitHub Actions 正确显示失败。

## 本地测试

    python -m pip install requests
    python -m unittest discover -s tests -v

单元测试使用模拟 HTTP 请求，不会发起真实 GLaDOS 签到。
