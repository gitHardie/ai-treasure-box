export default function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Hero */}
      <div className="text-center py-8">
        <span className="text-6xl mb-4 block">🧰</span>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 bg-clip-text text-transparent">
          AI 百宝箱
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-3 text-lg">
          一站式 AI 工具聚合平台
        </p>
      </div>

      {/* About section */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
          <span>✨</span> 关于项目
        </h2>
        <div className="space-y-3 text-slate-600 dark:text-slate-400 leading-relaxed">
          <p>
            <strong className="text-slate-900 dark:text-white">AI百宝箱</strong> 是一个自动化的 AI 工具聚合平台。
            我们从 GitHub Trending、Product Hunt、Hugging Face 等多个来源自动采集优秀的 AI 开源工具，
            帮助你快速发现和使用最新的 AI 技术。
          </p>
          <p>
            平台通过 Python 数据采集管道定时抓取和整理数据，前端使用 React 构建，
            部署在 GitHub Pages 上，通过 GitHub Actions 实现自动化构建和部署。
          </p>
        </div>
      </div>

      {/* Data sources */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
          <span>📡</span> 数据来源
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex items-start gap-3 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
            <span className="text-2xl">🐙</span>
            <div>
              <h3 className="font-medium text-slate-900 dark:text-white">GitHub Trending</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">每日热门 AI 开源项目</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
            <span className="text-2xl">🚀</span>
            <div>
              <h3 className="font-medium text-slate-900 dark:text-white">Product Hunt</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">最新上线的 AI 产品</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
            <span className="text-2xl">🤗</span>
            <div>
              <h3 className="font-medium text-slate-900 dark:text-white">Hugging Face</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">热门 AI 模型和数据集</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
            <span className="text-2xl">📰</span>
            <div>
              <h3 className="font-medium text-slate-900 dark:text-white">AI 资讯</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">行业动态与新闻</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tech stack */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
          <span>⚙️</span> 技术栈
        </h2>
        <div className="flex flex-wrap gap-2">
          {['Python', 'React', 'TypeScript', 'Vite', 'Tailwind CSS', 'GitHub Actions', 'GitHub Pages'].map(tech => (
            <span key={tech} className="badge bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-800">
              {tech}
            </span>
          ))}
        </div>
      </div>

      {/* Links */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
          <span>🔗</span> 相关链接
        </h2>
        <div className="space-y-3">
          <a
            href="https://github.com/gitHardie/ai-treasure-box"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group"
          >
            <svg className="w-5 h-5 text-slate-600 dark:text-slate-400" fill="currentColor" viewBox="0 0 24 24">
              <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
            </svg>
            <div>
              <div className="text-sm font-medium text-slate-900 dark:text-white group-hover:text-indigo-500 transition-colors">
                GitHub 仓库
              </div>
              <div className="text-xs text-slate-500">gitHardie/ai-treasure-box</div>
            </div>
          </a>
          <a
            href="https://afterai.tech"
            className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group"
          >
            <svg className="w-5 h-5 text-slate-600 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
            </svg>
            <div>
              <div className="text-sm font-medium text-slate-900 dark:text-white group-hover:text-indigo-500 transition-colors">
                网站地址
              </div>
              <div className="text-xs text-slate-500">afterai.tech</div>
            </div>
          </a>
        </div>
      </div>

      {/* Footer */}
      <div className="text-center py-6 text-sm text-slate-500 dark:text-slate-500">
        <p>© {new Date().getFullYear()} AI百宝箱 · 让 AI 工具触手可及</p>
      </div>
    </div>
  )
}
