import { getAnalytics } from '@/lib/analytics'
import Dashboard from '@/components/Dashboard'

export const dynamic = 'force-dynamic'

export default async function Home() {
  const data = await getAnalytics()
  return <Dashboard data={data} />
}
