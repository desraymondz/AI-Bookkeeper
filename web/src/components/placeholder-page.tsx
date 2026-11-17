import { EmptyState } from '@/components/states'

export function PlaceholderSection({ title }: { title: string }) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-lg font-semibold">{title}</h2>
      <EmptyState message="Not built yet." />
    </section>
  )
}
