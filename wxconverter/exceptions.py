"""
自定义异常类

定义了本工具使用的异常层次结构：
- WxConverterError: 所有异常的基类
- CaptchaError: 微信验证码/环境异常
- NetworkError: 网络请求失败
- ParseError: HTML 解析失败
"""


class WxConverterError(Exception):
    """
    本工具所有异常的基类

    捕获此异常可以处理所有本工具产生的错误。
    """
    pass


class CaptchaError(WxConverterError):
    """
    微信显示验证码/环境异常页面

    当微信检测到异常访问时会显示验证页面，而非正常文章内容。
    解决方法：使用 --no-headless 参数手动处理验证码。
    """
    pass


class NetworkError(WxConverterError):
    """
    网络请求失败

    在所有重试次数用尽后仍无法获取页面内容时抛出。
    可能原因：网络连接问题、微信服务器无响应等。
    """
    pass


class ParseError(WxConverterError):
    """
    HTML 解析失败

    当页面内容无法解析为预期的文章结构时抛出。
    可能原因：文章不存在、页面结构变化、内容为空等。
    """
    pass


# 向后兼容：保留旧的异常类名
WechatToMdError = WxConverterError
