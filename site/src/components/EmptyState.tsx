interface Props {
  icon?: string
  title: string
  description?: string
}

export default function EmptyState({ icon = '📭', title, description }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <span className="text-5xl mb-4">{icon}</span>
      <h3 className="text-lg font-medium text-slate-700 dark:text-slate-300 mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-slate-500 dark:text-slate-500 max-w-sm">{description}</p>
      )}
    </div>
  )
}
