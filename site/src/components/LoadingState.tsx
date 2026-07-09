export default function LoadingState({ message = '加载中...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="relative">
        <div className="w-12 h-12 rounded-full border-4 border-slate-200 dark:border-slate-700"></div>
        <div className="absolute top-0 left-0 w-12 h-12 rounded-full border-4 border-transparent border-t-indigo-500 animate-spin"></div>
      </div>
      <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">{message}</p>
    </div>
  )
}
