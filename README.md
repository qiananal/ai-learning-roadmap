# AI Learning Roadmap

这是一个基于 VitePress 的知识库站点，用于展示人工智能、后端工程化、Python 与相关技术笔记。

## 如何运行

### 1. 安装依赖

在项目根目录执行：

```bash
npm install
```

### 2. 启动本地预览

```bash
npm run dev
```

启动成功后，终端会显示本地访问地址，通常是：

```text
http://localhost:5173/
```

### 3. 如何打开这个页面

在浏览器中访问上面的地址即可打开站点首页。

如果你想查看某篇内容，可以直接访问对应的页面路径，例如：

- `/`：首页
- `/demo`：Demo 页面
- `/FastAPI/README`：FastAPI 说明页
- `/Database/README`：数据库实践页面
- `/Streamlit/README`：Streamlit 页面
- `/python/README`：Python 使用教程页面

## 目录说明

当前项目主要包含以下内容：

```text
.
├── .vitepress/           # VitePress 配置与主题设置
├── Database/             # 数据库实践
├── Docker/               # Docker 容器化
├── FastAPI/              # FastAPI 服务开发
├── git/                  # Git 使用说明
├── LangChain/            # LangChain 与 RAG
├── python/               # Python 基础与工程化
├── Streamlit/            # Streamlit 交互界面
├── DistributedAsynchronousTask/  # 分布式异步任务
├── demo.md               # 快速开始示例
├── index.md              # 站点首页
├── README.md             # 项目说明
```

说明：
- 根目录下的 `.md` 文件会被自动识别为页面
- 子目录中的 `README.md` 会作为该目录下的入口页面
- 侧边栏内容由 [.vitepress/config.mjs](.vitepress/config.mjs) 控制

## 如何更新内容

### 1. 新增一篇文章

可以在任意目录下创建新的 `.md` 文件，例如：

```bash
mkdir -p MyTopic
notepad MyTopic/README.md
```

### 2. 本地预览更新

保存后，运行：

```bash
npm run dev
```

页面会自动刷新，可以直接在浏览器中查看更新结果。

### 3. 让新内容出现在侧边栏

如果希望新文章出现在左侧菜单中，需要手动在 [.vitepress/config.mjs](.vitepress/config.mjs) 里添加对应链接，例如：

```js
sidebar: {
  '/': [
    {
      text: '新模块',
      items: [
        { text: '介绍', link: '/MyTopic/README' }
      ]
    }
  ]
}
```

### 4. 更新完成后提交

如果你准备把内容发布到仓库，可以执行：

```bash
git add .
git commit -m "更新文档内容"
git push
```

## 常见问题

- 如果页面没有显示侧边栏，请检查 [.vitepress/config.mjs](.vitepress/config.mjs)
- 如果某个子页面打不开，确认对应文件名是否为 `README.md`
- 如果新增内容后没有出现在菜单中，需要手动在配置文件中添加链接

## 构建发布

```bash
npm run build
```

构建结果会输出到 `.vitepress/dist` 目录。


