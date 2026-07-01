import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "AI Learning Roadmap",
  description: "我的人工智能与全栈工程笔记",
  themeConfig: {
    // 顶部右侧导航栏
    nav: [
      { text: '首页', link: '/' },
      { text: '技术全景', link: '/核心全链路：无死角技术全景拆解' }
    ],

    // 🌟 注意：这里改成了对象格式，'/' 代表全站所有路径都通用这一套侧边栏 🌟
    sidebar: {
      '/': [
        {
          text: '🗺️ 核心全景',
          items: [
            { text: '无死角技术全景拆解', link: '/核心全链路：无死角技术全景拆解' },
            { text: '快速开始 (Demo)', link: '/demo' }
          ]
        },
        {
          text: '🚀 后端与工程化',
          items: [
            { text: 'FastAPI 工业级推理服务', link: '/FastAPI/README' }, 
            { text: 'Docker 容器化', link: '/Docker/README' },
            { text: '数据库实践', link: '/Database/README' }
          ]
        },
        {
          text: '🧠 AI 与大模型生态',
          items: [
            { text: '分布式异步任务', link: '/DistributedAsynchronousTask/README' },
            { text: 'LangChain 与 RAG 实践', link: '/LangChain/README' },
            { text: 'Streamlit 交互界面', link: '/Streamlit/README' },
            { text: '长任务状态追踪与大屏监控', link: '/长任务状态追踪与大屏监控对齐/README' }
          ]
        },
        {
          text: '🛠️ 基础工具',
          items: [
            { text: 'Git 使用教程', link: '/git/README' },
            { text: 'Python 基础', link: '/python/README' }
          ]
        }
      ]
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/qiananal/ai-learning-roadmap' }
    ]
  }
})
