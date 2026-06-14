/** Italic scientific name — lit-room local typography primitive */
export function LitScientificName({
  name,
  className = "",
}: {
  name: string
  className?: string
}) {
  return (
    <em className={`lit-scientific taxon-name not-italic font-medium tracking-tight ${className}`}>
      <span className="italic">{name}</span>
    </em>
  )
}
