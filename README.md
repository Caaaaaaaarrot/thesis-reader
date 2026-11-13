# Thesis-Reader

本地论文库与 AI 速读助手。沿用 `npm run dev` 启动 Electron、React 界面和 Python 后端。

## 启动

```powershell
python -m pip install fastapi "uvicorn[standard]" pydantic pymupdf watchdog
npm install
npm run dev
```

当前 Windows 启动脚本使用 `F:/anaconda/python.exe`，Python 依赖需安装到这个环境。本轮保持原有开发启动方式，暂未制作安装包。

## 目录自动监听

- 把 PDF 放到项目根目录的 `papers/` 或其子目录，等待文件写入完成后会自动索引。
- 已有论文在启动时补齐索引；新增、修改、移动、重命名及移除会更新论文列表和知识图谱。
- 重命名依据文件内容识别，保留论文 ID、手动标题、标签、笔记和速读结果。
- 文件内容改变后清除旧速读缓存；外部移除仅隐藏条目并保留元数据。同一文件重新放回目录时可重新关联。
- 手动导入与监听共用索引逻辑，导入目录内文件不会自我复制。
- 侧栏显示连接状态；设置中的“论文库与目录监听”显示实际目录、扫描问题及重新扫描按钮。
- 文件写入触发约 0.8 秒防抖；前端约 2 秒检查一次变更。另有每 20 秒全目录校对以恢复遗漏事件。

## C++ 页面评分

速读选页接入 C++17 多关键词匹配模块，通过标准 C ABI 和 Python ctypes 批量处理页面。关键词、角色权重和 Python 回退保持在 Python 中；PDF 渲染继续使用 PyMuPDF。

```powershell
npm run native:build
```

需要本地 C++17 编译器：优先使用 MinGW-w64 的 `g++` 或 `clang++`；也可使用 CMake 和 MSVC。无需安装 pybind11 或 Python 开发头文件。

`npm run dev` 会先尝试编译；缺少工具链时会提示并继续使用 Python。设置页可查看实际启用的评分引擎。修改编译产物后需重启后端。

可选：`THESIS_READER_NATIVE=0` 强制使用 Python；`CXX` 指定编译器。仅比较页面评分性能：

```powershell
python scripts/benchmark_scorer.py
```

## 知识图谱

点击侧栏“知识图谱”。蓝色节点是论文，紫色是标签，绿色是会议/期刊，橙色是年份；连线表示属性归属，不表示论文引用或 AI 推断的语义关系。

- 点击论文查看详情；点击属性节点突出显示关联论文。
- 拖动节点和空白画布，滚轮或按钮缩放，“重置”适配当前图谱。
- 可单独开关标签、会议和年份关系，显示论文标题。
- 搜索、已读状态及侧栏筛选同时作用于图谱；文件同步和元数据编辑后自动更新。
- 为控制布局开销，一次显示当前排序下前 200 篇论文，超过时会提示，可通过筛选缩小范围。

## 验证

```powershell
python -m pip install httpx
npm test
npx tsc --noEmit -p tsconfig.json
npm run build
```

Python 测试使用 `data/test-workspaces/` 内的独立临时库，涵盖真实目录监听、批量写入、移动、移除、恢复关联、并发扫描、手动导入和 C++/Python 一致性。`npm test` 也会验证前端图谱构建。未编译 C++ 时，其专项测试会明确跳过。

运行数据在 `papers/` 与 `data/`。远程模型配置与原有速读功能保持现状。
