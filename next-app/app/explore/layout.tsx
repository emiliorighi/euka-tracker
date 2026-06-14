export default function ExploreLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col p-4 md:p-5">{children}</div>
  )
}
