"""
MCP 服务器入口点

启动 wxconverter MCP 服务器，供 AI 客户端调用。
"""

from wxconverter.server import run_server

if __name__ == "__main__":
    run_server()
