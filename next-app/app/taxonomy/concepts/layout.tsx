export default function TaxonomyConceptsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-x-hidden p-4 md:p-5">
      {children}
    </div>
  )
}
