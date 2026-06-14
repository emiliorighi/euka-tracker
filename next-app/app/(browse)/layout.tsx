export default function BrowseLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="mx-auto w-full max-w-7xl flex-1 p-5 md:p-8">{children}</div>
  )
}
