from fastapi import FastAPI, Depends, HTTPException
from typing import Generator, Annotated
from fastapi.testclient import TestClient

app = FastAPI()

# --- 1. 模拟数据库 Session ---
class MockSession:
    def __init__(self):
        print("🟢 [DB] Session 对象创建 (__init__)")
    
    def __enter__(self):
        print("🔵 [DB] 进入上下文 (__enter__)")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print(f"🔴 [DB] 捕获到异常: {exc_type.__name__}: {exc_val}")
            print("🟣 [DB] 执行回滚 (Rollback) 逻辑...")
        else:
            print("🟣 [DB] 执行提交 (Commit) 逻辑...")
        
        print("🟤 [DB] 关闭连接 (close)")
        # 返回 False 让异常继续向上抛出（如果有的话）
        return False

# --- 2. 核心依赖生成器 (被验证的主角) ---
def get_db() -> Generator[MockSession, None, None]:
    print("\n" + "="*50)
    print(">>> [Dep] 1. 依赖函数开始执行")
    
    session = MockSession()
    session.__enter__()
    
    try:
        print(">>> [Dep] 2. 到达 yield，暂停执行，将 session 交给路由...")
        yield session  # <--- 第一次 next() 停在这里
        
        # 下面的代码在路由执行完后才会运行
        print(">>> [Dep] 3. 路由结束，生成器恢复执行 (yield 之后)")
    finally:
        print(">>> [Dep] 4. 进入 finally 块，执行清理")
        session.__exit__(None, None, None)
        print(">>> [Dep] 5. 依赖函数彻底结束")
    print("="*50 + "\n")

# 类型别名
SessionDep = Annotated[MockSession, Depends(get_db)]

# --- 3. 路由 A: 正常流程 ---
@app.get("/normal")
def normal_route(session: SessionDep):
    print(">>> [Route] 🚀 [正常] 业务逻辑执行中...")
    print(">>> [Route] 💾 [正常] 查询数据...")
    return {"status": "success", "msg": "正常完成"}

# --- 4. 路由 B: 异常流程 ---
@app.get("/error")
def error_route(session: SessionDep):
    print(">>> [Route] 🚀 [异常] 业务逻辑执行中...")
    print(">>> [Route] 💥 [异常] 故意抛出错误!")
    raise HTTPException(status_code=500, detail="模拟服务器崩溃")

# --- 5. 使用 TestClient 进行自动化验证 ---
if __name__ == "__main__":
    # 实例化客户端 (这会触发应用启动逻辑)
    client = TestClient(app)
    
    print("\n🧪 测试场景 1: 正常请求 (/normal)")
    print("-" * 30)
    response1 = client.get("/normal")
    print(f"响应状态码: {response1.status_code}")
    print(f"响应内容: {response1.json()}")
    
    print("\n\n🧪 测试场景 2: 异常请求 (/error)")
    print("-" * 30)
    try:
        response2 = client.get("/error")
    except Exception as e:
        # TestClient 默认会将 HTTP 500 异常抛出来，或者我们可以配置 raise_server_exceptions=False
        # 这里我们捕获它以便观察后续的清理日志
        print(f"客户端捕获到异常: {e}")
    
    # 注意：即使上面报错了，上面的日志中应该已经打印了 "finally" 和 "close"
    
    print("\n✅ 验证结束。请检查上方日志中 'yield 之后' 的代码是否被执行。")