export function PageHeader({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow?: string
  title: string
  description?: string
  children?: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-4 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
      <div className="space-y-1.5">
        {eyebrow && (
          <p className="text-xs font-medium uppercase tracking-widest text-primary">{eyebrow}</p>
        )}
        <h1 className="text-balance text-2xl font-semibold tracking-tight md:text-3xl">{title}</h1>
        {description && (
          <p className="max-w-2xl text-pretty text-sm leading-relaxed text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      {children && <div className="flex shrink-0 items-center gap-2">{children}</div>}
    </div>
  )
}
